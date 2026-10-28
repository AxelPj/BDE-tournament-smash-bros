import random

import pytest
from sqlalchemy import func, select

from app.bets import service as bets
from app.duels import service as duels
from app.economy.models import TiltTransaction, TransactionKind
from app.economy.service import InsufficientFundsError, record_transaction
from app.tournaments import service as tournaments
from app.users.models import User
from app.users.service import create_user
from tests.test_scores import get, setup_tournament, win
from tests.test_tournaments_api import PASSWORD, login


def player(db, name, balance=1000, password=None):
    user = create_user(db, name, name.title(), password)
    if balance:
        record_transaction(db, user.id, balance, TransactionKind.ADMIN_ADJUSTMENT, "départ")
        db.commit()
    return user


def balance(db, user):
    db.expire_all()
    return db.get(User, user.id).balance


@pytest.fixture
def duel_setup(db):
    """Duel Mario contre Luigi validé (paris ouverts) et trois spectateurs."""
    admin = player(db, "admin", 0)
    admin.is_admin = True
    mario, luigi = player(db, "mario"), player(db, "luigi")
    a, b, c = player(db, "a"), player(db, "b"), player(db, "c")
    duel = duels.create_duel(db, mario, luigi.id)
    duels.respond(db, duel, luigi, accept=True)
    duels.validate(db, duel, admin)
    return duel, admin, mario, luigi, a, b, c


def finish(db, duel, challenger_wins=True):
    if duel.status.value == "validated":
        duels.start(db, duel)
    duels.report_result(db, duel, *((2, 0) if challenger_wins else (0, 2)))


# --- Calcul des gains ---


def test_parimutuel_payout(db, duel_setup):
    duel, _, mario, luigi, a, b, c = duel_setup
    bets.place_duel_bet(db, a, duel, mario.id, 200)
    bets.place_duel_bet(db, b, duel, mario.id, 100)
    bets.place_duel_bet(db, c, duel, luigi.id, 100)

    finish(db, duel)  # Mario gagne : 400 Tilt à partager entre 300 misés sur lui

    assert balance(db, a) == 800 + 200 * 400 // 300  # 266
    assert balance(db, b) == 900 + 100 * 400 // 300  # 133
    assert balance(db, c) == 900


def test_nobody_on_winner_means_refund(db, duel_setup):
    duel, _, mario, _, a, _, _ = duel_setup
    bets.place_duel_bet(db, a, duel, mario.id, 100)

    finish(db, duel, challenger_wins=False)

    assert balance(db, a) == 1000


def test_cancelled_duel_refunds(db, duel_setup):
    duel, admin, mario, luigi, a, _, c = duel_setup
    bets.place_duel_bet(db, a, duel, mario.id, 100)
    bets.place_duel_bet(db, c, duel, luigi.id, 50)
    duels.start(db, duel)

    duels.cancel(db, duel, admin)

    assert (balance(db, a), balance(db, c)) == (1000, 1000)


def test_correction_moves_payouts(db, duel_setup):
    duel, _, mario, luigi, a, b, c = duel_setup
    bets.place_duel_bet(db, a, duel, mario.id, 200)
    bets.place_duel_bet(db, b, duel, mario.id, 100)
    bets.place_duel_bet(db, c, duel, luigi.id, 100)
    finish(db, duel)

    finish(db, duel, challenger_wins=False)  # correction : Luigi a gagné

    assert (balance(db, a), balance(db, b), balance(db, c)) == (800, 900, 900 + 400)


def test_reclaimed_payout_never_makes_balance_negative(db, duel_setup):
    duel, _, mario, luigi, a, _, c = duel_setup
    bets.place_duel_bet(db, a, duel, mario.id, 1000)
    bets.place_duel_bet(db, c, duel, luigi.id, 1000)
    finish(db, duel)  # a : 2000
    record_transaction(db, a.id, -2000, TransactionKind.ADMIN_ADJUSTMENT, "dépensé")
    db.commit()

    finish(db, duel, challenger_wins=False)

    assert balance(db, a) == 0
    assert balance(db, c) == 2000


# --- Règles de prise de pari ---


def test_betting_window(db, duel_setup):
    duel, admin, mario, luigi, a, _, _ = duel_setup
    other = duels.create_duel(db, a, mario.id)  # pas encore validé
    with pytest.raises(bets.BettingClosedError):
        bets.place_duel_bet(db, luigi, other, mario.id, 10)

    duels.start(db, duel)
    with pytest.raises(bets.BettingClosedError):
        bets.place_duel_bet(db, a, duel, mario.id, 10)


def test_players_can_only_bet_on_themselves(db, duel_setup):
    duel, _, mario, luigi, _, _, _ = duel_setup

    with pytest.raises(bets.ForbiddenBetError):
        bets.place_duel_bet(db, mario, duel, luigi.id, 10)
    bets.place_duel_bet(db, mario, duel, mario.id, 10)


def test_one_side_per_bettor_but_several_bets_allowed(db, duel_setup):
    duel, _, mario, luigi, a, _, _ = duel_setup
    bets.place_duel_bet(db, a, duel, mario.id, 10)
    bets.place_duel_bet(db, a, duel, mario.id, 20)

    with pytest.raises(bets.ForbiddenBetError):
        bets.place_duel_bet(db, a, duel, luigi.id, 10)
    assert balance(db, a) == 970


def test_invalid_bets(db, duel_setup):
    duel, _, mario, _, a, _, _ = duel_setup

    with pytest.raises(ValueError):
        bets.place_duel_bet(db, a, duel, a.id, 10)  # a ne joue pas ce duel
    with pytest.raises(InsufficientFundsError):
        bets.place_duel_bet(db, a, duel, mario.id, 1001)
    db.rollback()
    assert balance(db, a) == 1000


# --- Matchs de tournoi ---


@pytest.fixture
def bracket(db):
    """Tournoi à 4 (W1-1 = p0 contre p3, W1-2 = p1 contre p2) et un spectateur."""
    t, players = setup_tournament(db, 4)
    return t, [db.get(User, p) for p in players], player(db, "fan")


def test_tournament_match_bet_settled_by_score(db, bracket):
    t, (p0, p1, p2, p3), fan = bracket
    bets.place_match_bet(db, fan, t, "W1-1", p0.id, 100)
    bets.place_match_bet(db, p3, t, "W1-1", p3.id, 100)  # 100 de récompense de participation

    win(db, t, "W1-1")  # p0 gagne

    assert balance(db, fan) == 1000 + 100  # 200 / 100 misés sur p0 : cote 2
    assert get(t, "W1-1").betting_open is False


def test_start_closes_tournament_bets(db, bracket):
    t, (p0, *_), fan = bracket
    tournaments.start_match(db, t, "W1-1")

    with pytest.raises(bets.BettingClosedError):
        bets.place_match_bet(db, fan, t, "W1-1", p0.id, 10)
    with pytest.raises(tournaments.TournamentStateError):
        tournaments.start_match(db, t, "W1-1")
    with pytest.raises(bets.BettingClosedError):
        bets.place_match_bet(db, fan, t, "W2-1", p0.id, 10)  # adversaire pas encore connu


def test_correction_refunds_bets_on_changed_pairing_and_reopens_betting(db, bracket):
    t, (p0, p1, p2, p3), fan = bracket
    win(db, t, "W1-1")
    win(db, t, "W1-2")
    bets.place_match_bet(db, fan, t, "W2-1", p0.id, 100)  # p0 contre p1
    tournaments.start_match(db, t, "W2-1")

    win(db, t, "W1-1", first_player_wins=False)  # correction : W2-1 devient p3 contre p1

    assert balance(db, fan) == 1000
    w2 = get(t, "W2-1")
    assert (w2.player1_id, w2.betting_open) == (p3.id, True)


def test_cancelled_score_reclaims_payout_and_keeps_betting_closed(db, bracket):
    t, (p0, *_), fan = bracket
    bets.place_match_bet(db, fan, t, "W1-1", p0.id, 100)
    win(db, t, "W1-1")  # seul parieur, sur le vainqueur : remboursé (cote 1)

    tournaments.cancel_score(db, t, "W1-1")

    assert balance(db, fan) == 900  # pari en attente du nouveau résultat
    assert get(t, "W1-1").betting_open is False  # le match a déjà été joué


def test_reset_bracket_refunds_bets(db, bracket):
    t, (p0, *_), fan = bracket
    bets.place_match_bet(db, fan, t, "W1-1", p0.id, 100)

    tournaments.reset_bracket(db, t)

    assert balance(db, fan) == 1000


@pytest.mark.parametrize("seed", range(5))
def test_random_tournament_with_bets_conserves_tilt(db, seed):
    """Les gains d'un match ne dépassent jamais les mises, et chaque solde
    reste égal à la somme de son journal, malgré les corrections."""
    rng = random.Random(seed)
    t, ids = setup_tournament(db, 6)
    fans = [player(db, f"fan{i}") for i in range(4)]
    corrections = 8
    while True:
        open_matches = [m for m in t.matches if m.betting_open]
        for match in rng.sample(open_matches, min(2, len(open_matches))):
            fan = rng.choice(fans)
            pick = rng.choice([match.player1_id, match.player2_id])
            try:
                bets.place_match_bet(db, fan, t, match.code, pick, rng.randint(1, 50))
            except (bets.ForbiddenBetError, InsufficientFundsError):
                db.rollback()
        played = [m for m in t.matches if m.result_order is not None]
        if corrections and played and rng.random() < 0.3:
            corrections -= 1
            win(db, t, rng.choice(played).code, rng.random() < 0.5)
            continue
        ready = [m for m in t.matches if m.status.value == "ready"]
        if not ready:
            break
        win(db, t, rng.choice(ready).code, rng.random() < 0.5)

    def total(kind):
        return db.scalar(select(func.coalesce(func.sum(TiltTransaction.amount), 0)).where(TiltTransaction.kind == kind))

    assert total(TransactionKind.BET_STAKE) < 0 and total(TransactionKind.BET_PAYOUT) > 0
    assert total(TransactionKind.BET_PAYOUT) <= -total(TransactionKind.BET_STAKE)
    for user_id in ids + [f.id for f in fans]:
        journal = db.scalar(select(func.sum(TiltTransaction.amount)).where(TiltTransaction.user_id == user_id))
        assert balance(db, db.get(User, user_id)) == journal >= 0


# --- API ---


def test_api_bets(client, db):
    admin = player(db, "admin", 0, PASSWORD)
    admin.is_admin = True
    db.commit()
    mario, luigi = player(db, "mario", password=PASSWORD), player(db, "luigi", password=PASSWORD)
    player(db, "fan", password=PASSWORD)
    admin_c, mario_c, luigi_c, fan_c = (login(n) for n in ("admin", "mario", "luigi", "fan"))

    duel_id = mario_c.post("/api/duels", json={"opponent_id": luigi.id}).json()["id"]
    luigi_c.post(f"/api/duels/{duel_id}/accept")
    url = f"/api/duels/{duel_id}/bets"
    assert fan_c.post(url, json={"picked_player_id": mario.id, "amount": 10}).status_code == 409
    assert admin_c.post(f"/api/admin/duels/{duel_id}/validate").json()["betting_open"] is True

    assert fan_c.post(url, json={"picked_player_id": mario.id, "amount": 300}).status_code == 201
    assert mario_c.post(url, json={"picked_player_id": luigi.id, "amount": 10}).status_code == 403
    assert luigi_c.post(url, json={"picked_player_id": luigi.id, "amount": 100}).status_code == 201
    assert fan_c.post(url, json={"picked_player_id": mario.id, "amount": 0}).status_code == 422
    assert fan_c.post(url, json={"picked_player_id": mario.id, "amount": 5000}).status_code == 409

    market = fan_c.get(url).json()
    assert market["total"] == 400
    odds = {p["user_id"]: p["odds"] for p in market["players"]}
    assert odds == {mario.id: 1.33, luigi.id: 4.0}
    assert fan_c.get("/api/bets/mine").json()[0]["status"] == "open"

    admin_c.post(f"/api/admin/duels/{duel_id}/start")
    assert fan_c.get("/api/bets/mine").json()[0]["status"] == "closed"
    admin_c.put(f"/api/admin/duels/{duel_id}/result", json={"challenger_score": 2, "opponent_score": 1})

    mine = fan_c.get("/api/bets/mine").json()[0]
    assert (mine["status"], mine["payout"]) == ("won", 400)
    assert luigi_c.get("/api/bets/mine").json()[0]["status"] == "lost"
    assert fan_c.get("/api/auth/me").json()["balance"] == 1000 - 300 + 400
