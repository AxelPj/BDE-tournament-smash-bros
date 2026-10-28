"""Saisie, correction et annulation des scores (service + API)."""

import random
from collections import Counter

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.tournaments import service
from app.tournaments.bracket import MatchStatus
from app.tournaments.models import Tournament, TournamentStatus
from app.users.service import create_user


def setup_tournament(db, n, seeded=None):
    """Tournoi généré à n joueurs. Par défaut, têtes de série dans l'ordre de création."""
    # Comptes sans mot de passe : évite le coût du hachage dans les tests.
    users = [create_user(db, f"p{i}", f"P{i}", None) for i in range(n)]
    tournament = service.create_tournament(db, "Test")
    for user in users:
        service.add_participant(db, tournament, user.id, by_admin=True)
    order = users if seeded is None else seeded(users)
    service.set_seeds(db, tournament, [u.id for u in order])
    service.generate_bracket(db, tournament, rng=random.Random(0))
    return tournament, [u.id for u in users]


def get(tournament, code):
    return next(m for m in tournament.matches if m.code == code)


def win(db, tournament, code, first_player_wins=True):
    score = (2, 0) if first_player_wins else (0, 2)
    return service.report_score(db, tournament, code, *score)


# 4 joueurs, têtes de série 0..3 : W1-1 = p0 contre p3, W1-2 = p1 contre p2.


def test_report_score_advances_players(db):
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)

    assert service.report_score(db, t, "W1-1", 2, 1) == []

    match = get(t, "W1-1")
    assert (match.winner_id, match.score1, match.score2) == (p0, 2, 1)
    assert match.status is MatchStatus.COMPLETED
    assert get(t, "W2-1").player1_id == p0
    assert get(t, "L1-1").player1_id == p3


def test_report_score_errors(db):
    t, _ = setup_tournament(db, 4)

    with pytest.raises(ValueError):
        service.report_score(db, t, "W1-1", 1, 1)  # match nul
    with pytest.raises(service.TournamentStateError):
        win(db, t, "W2-1")  # adversaires pas encore connus
    with pytest.raises(service.NotFoundError):
        win(db, t, "W9-9")


def test_cannot_score_a_bye_or_before_generation(db):
    t, _ = setup_tournament(db, 3)  # p0 a un bye en W1-1
    with pytest.raises(service.TournamentStateError):
        win(db, t, "W1-1")

    other = service.create_tournament(db, "Pas généré")
    with pytest.raises(service.TournamentStateError):
        win(db, other, "W1-1")


def test_correction_keeping_the_winner_keeps_later_results(db):
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)
    win(db, t, "W1-1")
    win(db, t, "W1-2")
    win(db, t, "W2-1")  # p0 bat p1

    assert service.report_score(db, t, "W1-1", 2, 1) == []

    assert (get(t, "W1-1").score1, get(t, "W1-1").score2) == (2, 1)
    assert get(t, "W2-1").winner_id == p0


def test_correction_changing_the_winner_invalidates_dependent_matches(db):
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)
    win(db, t, "W1-1")  # p0 bat p3
    win(db, t, "W1-2")  # p1 bat p2
    win(db, t, "W2-1")  # p0 bat p1
    win(db, t, "L1-1")  # p3 bat p2

    invalidated = win(db, t, "W1-1", first_player_wins=False)  # en fait p3 a gagné

    assert invalidated == ["W2-1", "L1-1"]
    w2 = get(t, "W2-1")
    assert [w2.player1_id, w2.player2_id] == [p3, p1]
    assert w2.status is MatchStatus.READY
    assert w2.score1 is None and w2.winner_id is None
    l1 = get(t, "L1-1")
    assert [l1.player1_id, l1.player2_id] == [p0, p2]
    # W1-2 ne dépendait pas de W1-1 : conservé.
    assert get(t, "W1-2").winner_id == p1


def test_cancel_score(db):
    t, _ = setup_tournament(db, 4)
    win(db, t, "W1-1")

    assert service.cancel_score(db, t, "W1-1") == []

    match = get(t, "W1-1")
    assert match.status is MatchStatus.READY
    assert match.winner_id is None and match.result_order is None
    assert get(t, "W2-1").player1_id is None
    with pytest.raises(service.TournamentStateError):
        service.cancel_score(db, t, "W1-1")  # plus rien à annuler


def play_until_done(db, tournament, rng, corrections=0):
    """Joue le tournoi au hasard, en corrigeant parfois un match déjà joué."""
    while True:
        played = [m for m in tournament.matches if m.result_order is not None]
        if corrections and played and rng.random() < 0.2:
            corrections -= 1
            win(db, tournament, rng.choice(played).code, rng.random() < 0.5)
            continue
        ready = [m for m in tournament.matches if m.status is MatchStatus.READY]
        if not ready:
            return
        win(db, tournament, rng.choice(ready).code, rng.random() < 0.5)


def test_tournament_completes_and_grand_final_can_be_corrected(db):
    t, (p0, p1) = setup_tournament(db, 2)
    win(db, t, "W1-1")  # p0 bat p1
    win(db, t, "GF")  # p0 gagne encore : pas de reset

    assert t.status is TournamentStatus.COMPLETED
    assert t.champion_id == p0
    assert get(t, "GF-R").status is MatchStatus.SKIPPED

    win(db, t, "GF", first_player_wins=False)  # correction : p1 a gagné la GF

    assert t.status is TournamentStatus.IN_PROGRESS
    assert t.champion_id is None
    assert get(t, "GF-R").status is MatchStatus.READY


@pytest.mark.parametrize("n", [3, 5, 8, 11])
@pytest.mark.parametrize("seed", range(4))
def test_random_play_with_corrections_stays_consistent(db, n, seed):
    rng = random.Random(seed)
    t, players = setup_tournament(db, n, seeded=lambda users: rng.sample(users, len(users)))

    play_until_done(db, t, rng, corrections=10)

    assert t.status is TournamentStatus.COMPLETED
    played = [m for m in t.matches if m.result_order is not None]
    losses = Counter(
        m.player2_id if m.winner_id == m.player1_id else m.player1_id for m in played
    )
    assert all(losses[p] == 2 for p in players if p != t.champion_id)
    assert losses[t.champion_id] <= 1
    assert len(played) in (2 * n - 2, 2 * n - 1)


def test_reset_bracket_keeps_admin_seeds(db):
    t, (p0, p1, p2) = setup_tournament(db, 3, seeded=lambda users: users[2:])

    service.reset_bracket(db, t)

    assert t.status is TournamentStatus.REGISTRATION
    assert t.matches == []
    seeds = {p.user_id: (p.seed, p.bracket_seed) for p in t.participants}
    assert seeds == {p0: (None, None), p1: (None, None), p2: (1, None)}
    # On peut régénérer ensuite.
    service.generate_bracket(db, t)
    assert t.status is TournamentStatus.IN_PROGRESS


def test_reset_forbidden_once_a_score_exists(db):
    t, _ = setup_tournament(db, 4)
    win(db, t, "W1-1")

    with pytest.raises(service.TournamentStateError):
        service.reset_bracket(db, t)


def test_concurrent_modification_is_rejected(engine, db):
    t, _ = setup_tournament(db, 4)

    with Session(engine) as admin_a, Session(engine) as admin_b:
        ta = admin_a.get(Tournament, t.id)
        tb = admin_b.get(Tournament, t.id)
        _ = ta.matches, ta.participants, tb.matches, tb.participants  # chargés avant

        win(admin_a, ta, "W1-1")
        with pytest.raises(StaleDataError):
            win(admin_b, tb, "W1-2")  # basé sur une version périmée


# --- API ---


@pytest.fixture
def api_tournament(client, db):
    from tests.test_tournaments_api import PASSWORD, login

    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    create_user(db, "joueur", "Joueur", PASSWORD)
    t, players = setup_tournament(db, 4)
    return t.id, login("admin"), login("joueur")


def test_api_report_and_correct_score(api_tournament):
    tid, admin, _ = api_tournament
    url = f"/api/tournaments/{tid}/matches"

    response = admin.put(f"{url}/W1-1/score", json={"score1": 3, "score2": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["invalidated"] == []
    w1 = next(m for m in body["matches"] if m["code"] == "W1-1")
    assert (w1["score1"], w1["score2"], w1["status"]) == (3, 1, "completed")

    admin.put(f"{url}/W1-2/score", json={"score1": 2, "score2": 0})
    admin.put(f"{url}/W2-1/score", json={"score1": 2, "score2": 0})
    response = admin.put(f"{url}/W1-1/score", json={"score1": 0, "score2": 2})
    assert response.json()["invalidated"] == ["W2-1"]


def test_api_score_errors(api_tournament):
    tid, admin, player = api_tournament
    url = f"/api/tournaments/{tid}/matches"

    assert player.put(f"{url}/W1-1/score", json={"score1": 2, "score2": 0}).status_code == 403
    assert admin.put(f"{url}/W1-1/score", json={"score1": 1, "score2": 1}).status_code == 400
    assert admin.put(f"{url}/W1-1/score", json={"score1": -1, "score2": 2}).status_code == 422
    assert admin.put(f"{url}/W2-1/score", json={"score1": 2, "score2": 0}).status_code == 409
    assert admin.put(f"{url}/X/score", json={"score1": 2, "score2": 0}).status_code == 404


def test_api_cancel_score_and_reset(api_tournament):
    tid, admin, _ = api_tournament
    url = f"/api/tournaments/{tid}"

    admin.put(f"{url}/matches/W1-1/score", json={"score1": 2, "score2": 0})
    assert admin.post(f"{url}/reset").status_code == 409

    response = admin.delete(f"{url}/matches/W1-1/score")
    assert response.status_code == 200
    assert admin.post(f"{url}/reset").json()["status"] == "registration"
