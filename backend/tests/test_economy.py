import random

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.economy.models import TiltTransaction, TransactionKind
from app.economy.service import (
    InsufficientFundsError,
    UnknownUserError,
    list_transactions,
    record_transaction,
)
from app.users.service import create_user
from tests.test_tournaments_api import PASSWORD, login

KIND = TransactionKind.ADMIN_ADJUSTMENT


@pytest.fixture
def user(db):
    return create_user(db, "mario", "Mario", None)


def test_credit_and_debit(db, user):
    record_transaction(db, user.id, 100, KIND, "cadeau")
    tx = record_transaction(db, user.id, -30, KIND, "achat")
    db.commit()

    assert user.balance == 70
    assert (tx.amount, tx.balance_after) == (-30, 70)
    assert [t.amount for t in list_transactions(db, user.id, 10, 0)] == [-30, 100]


def test_insufficient_funds_changes_nothing(db, user):
    record_transaction(db, user.id, 10, KIND, "cadeau")

    with pytest.raises(InsufficientFundsError):
        record_transaction(db, user.id, -11, KIND, "trop cher")

    db.commit()
    assert user.balance == 10
    assert len(list_transactions(db, user.id, 10, 0)) == 1


def test_database_refuses_negative_balance(db, user):
    """Filet de sécurité : même une modification directe est refusée par la base."""
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE users SET balance = -1 WHERE id = :id"), {"id": user.id})


def test_reference_prevents_double_payment(db, user):
    first = record_transaction(db, user.id, 50, KIND, "récompense", reference="test:1")
    second = record_transaction(db, user.id, 50, KIND, "récompense", reference="test:1")
    db.commit()

    assert first.id == second.id
    assert user.balance == 50


def test_invalid_transactions(db, user):
    with pytest.raises(ValueError):
        record_transaction(db, user.id, 0, KIND, "rien")
    with pytest.raises(UnknownUserError):
        record_transaction(db, 999, 10, KIND, "fantôme")


def test_balance_always_equals_sum_of_journal(db, user):
    rng = random.Random(0)
    for _ in range(200):
        amount = rng.choice([-1, 1]) * rng.randint(1, 50)
        try:
            record_transaction(db, user.id, amount, KIND, "aléatoire")
        except InsufficientFundsError:
            pass
    db.commit()

    total = db.scalar(select(func.sum(TiltTransaction.amount)).where(TiltTransaction.user_id == user.id))
    assert user.balance == total >= 0


# --- API ---


@pytest.fixture
def accounts(client, db):
    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    player = create_user(db, "joueur", "Joueur", PASSWORD)
    return login("admin"), login("joueur"), player


def test_admin_adjusts_balance(accounts):
    admin, player_client, player = accounts
    url = f"/api/admin/users/{player.id}/tilt"

    response = admin.post(url, json={"amount": 200, "reason": "Bonus d'accueil"})
    assert response.status_code == 201
    assert response.json()["balance_after"] == 200

    assert admin.post(url, json={"amount": -50, "reason": "Correction"}).status_code == 201
    assert player_client.get("/api/auth/me").json()["balance"] == 150

    history = player_client.get("/api/wallet/transactions").json()
    assert [(t["amount"], t["description"]) for t in history] == [
        (-50, "Correction"),
        (200, "Bonus d'accueil"),
    ]
    assert history[0]["created_by_id"] is not None


def test_admin_adjustment_errors(accounts):
    admin, player_client, player = accounts
    url = f"/api/admin/users/{player.id}/tilt"

    assert player_client.post(url, json={"amount": 10, "reason": "triche"}).status_code == 403
    assert admin.post(url, json={"amount": -1, "reason": "x"}).status_code == 409
    assert admin.post(url, json={"amount": 0, "reason": "x"}).status_code == 400
    assert admin.post(url, json={"amount": 10, "reason": ""}).status_code == 422
    assert admin.post("/api/admin/users/999/tilt", json={"amount": 10, "reason": "x"}).status_code == 404


def test_players_only_see_their_own_history(accounts):
    admin, player_client, player = accounts
    admin.post(f"/api/admin/users/{player.id}/tilt", json={"amount": 10, "reason": "x"})

    assert admin.get("/api/wallet/transactions").json() == []
    assert player_client.get(f"/api/admin/users/{player.id}/transactions").status_code == 403
    assert len(admin.get(f"/api/admin/users/{player.id}/transactions").json()) == 1
