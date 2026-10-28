import random
from collections import Counter, defaultdict

import pytest
from sqlalchemy import func, select

from app.economy.models import TiltTransaction, TransactionKind
from app.economy.service import record_transaction
from app.tournaments import service
from app.tournaments.rewards import RewardSettings, placement_tiers
from app.users.models import User
from app.users.service import create_user
from tests.test_scores import play_until_done, setup_tournament, win
from tests.test_tournaments_api import PASSWORD, login


def balances(db, user_ids):
    db.expire_all()
    return [db.get(User, user_id).balance for user_id in user_ids]


def expected_balances(tournament, settings=RewardSettings()):
    """Ce que chaque joueur doit avoir d'après l'état final du tournoi."""
    expected = defaultdict(int)
    for participant in tournament.participants:
        expected[participant.user_id] += settings.participation
    for match in tournament.matches:
        if match.result_order is not None:
            expected[match.player1_id] += settings.match_played
            expected[match.player2_id] += settings.match_played
            expected[match.winner_id] += settings.match_won
    for user_id, tier in placement_tiers(tournament).items():
        expected[user_id] += getattr(settings, tier)
    return expected


def test_participation_paid_at_generation_and_taken_back_on_reset(db):
    t, ids = setup_tournament(db, 3)
    assert balances(db, ids) == [100, 100, 100]

    service.reset_bracket(db, t)
    assert balances(db, ids) == [0, 0, 0]

    service.generate_bracket(db, t)
    assert balances(db, ids) == [100, 100, 100]


def test_match_rewards_follow_corrections(db):
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)  # W1-1 = p0 contre p3

    win(db, t, "W1-1")
    assert balances(db, [p0, p3]) == [130, 110]  # 100 + 10 + 20 / 100 + 10

    win(db, t, "W1-1", first_player_wins=False)  # correction : p3 a gagné
    assert balances(db, [p0, p3]) == [110, 130]

    service.cancel_score(db, t, "W1-1")
    assert balances(db, [p0, p3]) == [100, 100]


def test_byes_are_not_rewarded(db):
    t, (p0, _, _) = setup_tournament(db, 3)  # p0 passe le 1er tour par un bye

    assert balances(db, [p0]) == [100]


def test_placement_tiers_favorites_win(db):
    """Le joueur 1 de chaque match gagne toujours : p0 champion,
    p3 remonte le bracket perdants jusqu'en finale."""
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)
    for code in ["W1-1", "W1-2", "W2-1", "L1-1", "L2-1", "GF"]:
        win(db, t, code)

    assert placement_tiers(t) == {p0: "champion", p3: "finalist", p1: "top4", p2: "top4"}
    assert balances(db, [p0, p1, p2, p3]) == [
        100 + 3 * 30 + 200,  # W1-1, W2-1, GF : 3 matchs gagnés, champion
        100 + 3 * 10 + 20 + 60,  # gagne W1-2, perd W2-1 et L2-1 : top 4
        100 + 2 * 10 + 60,  # perd W1-2 et L1-1 : top 4
        100 + 4 * 10 + 2 * 20 + 100,  # perd W1-1, gagne L1-1 et L2-1, perd GF : finaliste
    ]


@pytest.mark.parametrize(
    ("n", "tiers"),
    [
        (2, {"champion": 1, "finalist": 1}),
        (5, {"champion": 1, "finalist": 1, "top4": 2, "top8": 1}),
        (8, {"champion": 1, "finalist": 1, "top4": 2, "top8": 4}),
        (13, {"champion": 1, "finalist": 1, "top4": 2, "top8": 4}),
    ],
)
def test_placement_tier_counts(db, n, tiers):
    t, _ = setup_tournament(db, n)
    play_until_done(db, t, random.Random(n))

    assert Counter(placement_tiers(t).values()) == tiers


@pytest.mark.parametrize("n", [2, 5, 8, 13])
@pytest.mark.parametrize("seed", range(3))
def test_balances_match_final_state_after_corrections(db, n, seed):
    rng = random.Random(seed)
    t, ids = setup_tournament(db, n, seeded=lambda users: rng.sample(users, len(users)))

    play_until_done(db, t, rng, corrections=10)

    expected = expected_balances(t)
    assert balances(db, ids) == [expected[i] for i in ids]
    for user_id in ids:
        journal = db.scalar(
            select(func.sum(TiltTransaction.amount)).where(TiltTransaction.user_id == user_id)
        )
        assert journal == expected[user_id]


def test_reversal_never_makes_balance_negative(db):
    t, (p0, p1) = setup_tournament(db, 2)
    win(db, t, "W1-1")  # p0 : 130
    record_transaction(db, p0, -130, TransactionKind.ADMIN_ADJUSTMENT, "dépensé")
    db.commit()

    win(db, t, "W1-1", first_player_wins=False)  # p0 devrait rendre 20, mais a 0
    assert balances(db, [p0]) == [0]

    # Les 20 Tilt dus sont repris au recalcul suivant, une fois le solde suffisant.
    record_transaction(db, p0, 50, TransactionKind.ADMIN_ADJUSTMENT, "cadeau")
    db.commit()
    win(db, t, "GF")  # p1 gagne la GF : p0 finaliste (+10 match, +100)
    assert balances(db, [p0]) == [50 - 20 + 10 + 100]


def test_changing_amounts_adjusts_paid_rewards(db):
    t, ids = setup_tournament(db, 2)
    win(db, t, "W1-1")

    service.update_tournament(
        db, t, None, None, RewardSettings(participation=0, match_played=1, match_won=0)
    )

    assert balances(db, ids) == [1, 1]


# --- API ---


def test_api_reward_settings(client, db):
    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    admin = login("admin")

    response = admin.post("/api/tournaments", json={"name": "T", "rewards": {"participation": 5}})
    assert response.status_code == 201
    rewards = response.json()["rewards"]
    assert rewards["participation"] == 5
    assert rewards["champion"] == 200  # valeur par défaut

    tid = response.json()["id"]
    new = {**rewards, "match_won": 50}
    assert admin.patch(f"/api/tournaments/{tid}", json={"rewards": new}).json()["rewards"] == new

    bad = {**rewards, "champion": -1}
    assert admin.patch(f"/api/tournaments/{tid}", json={"rewards": bad}).status_code == 422
