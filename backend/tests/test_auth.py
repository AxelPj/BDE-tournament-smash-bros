from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.auth.dependencies import require_admin
from app.auth.models import AuthSession
from app.core.config import get_settings
from app.core.db import get_db
from app.users.service import create_user

COOKIE = get_settings().session_cookie_name


def register(client, username="Mario", password="itsame-mario"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "display_name": "Mario Bros", "password": password},
    )


def test_register_logs_in_and_normalizes_username(client):
    response = register(client)

    assert response.status_code == 201
    assert response.json()["username"] == "mario"
    assert "password_hash" not in response.json()
    assert COOKIE in client.cookies
    assert client.get("/api/auth/me").json()["username"] == "mario"


def test_register_duplicate_username_is_case_insensitive(client):
    register(client, "mario")

    assert register(client, "MARIO").status_code == 409


def test_register_rejects_invalid_input(client):
    assert register(client, username="a b").status_code == 422
    assert register(client, username="ab").status_code == 422
    assert register(client, password="court").status_code == 422


def test_login_with_valid_credentials(client, db):
    create_user(db, "luigi", "Luigi", "green-brother")

    response = client.post("/api/auth/login", json={"username": "Luigi", "password": "green-brother"})

    assert response.status_code == 200
    assert client.get("/api/auth/me").json()["username"] == "luigi"


def test_login_failures_return_same_error(client, db):
    create_user(db, "luigi", "Luigi", "green-brother")

    wrong_password = client.post("/api/auth/login", json={"username": "luigi", "password": "nope"})
    unknown_user = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_account_without_password_cannot_login(client, db):
    # Compte destiné à l'API 42 uniquement.
    create_user(db, "toad", "Toad", password=None)

    response = client.post("/api/auth/login", json={"username": "toad", "password": ""})

    assert response.status_code == 401


def test_me_requires_session(client):
    assert client.get("/api/auth/me").status_code == 401

    client.cookies.set(COOKIE, "jeton-invente")
    assert client.get("/api/auth/me").status_code == 401


def test_logout_invalidates_session_server_side(client, db):
    register(client)
    token = client.cookies[COOKIE]

    assert client.post("/api/auth/logout").status_code == 204
    assert db.scalars(select(AuthSession)).all() == []

    # Même si quelqu'un a gardé une copie du cookie, il n'est plus valable.
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401


def test_expired_session_is_rejected(client, db):
    register(client)
    db.execute(update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()

    assert client.get("/api/auth/me").status_code == 401


def test_session_token_is_not_stored_in_clear(client, db):
    register(client)

    stored = db.scalar(select(AuthSession.token_hash))
    assert stored != client.cookies[COOKIE]


def test_require_admin(db):
    """Route de test protégée par require_admin."""
    test_app = FastAPI()

    @test_app.get("/admin-only")
    def admin_only(admin=Depends(require_admin)):
        return {"ok": True}

    from app.auth.router import router

    test_app.include_router(router)
    test_app.dependency_overrides[get_db] = lambda: db
    create_user(db, "player", "Player", "password-1")
    create_user(db, "boss", "Boss", "password-2", is_admin=True)

    with TestClient(test_app) as client:
        assert client.get("/admin-only").status_code == 401

        client.post("/api/auth/login", json={"username": "player", "password": "password-1"})
        assert client.get("/admin-only").status_code == 403

        client.post("/api/auth/login", json={"username": "boss", "password": "password-2"})
        assert client.get("/admin-only").status_code == 200
