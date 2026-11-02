from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.auth import service as auth_service
from app.auth.dependencies import require_admin
from app.auth.models import AuthSession
from app.auth.service import Intra42Profile
from app.core.config import get_settings
from app.core.db import get_db
from app.users.service import create_user, get_user_by_username

COOKIE = get_settings().session_cookie_name
STATE_COOKIE = get_settings().oauth_state_cookie_name
REDIRECT_URI = "http://localhost:3000/auth/callback"


def oauth_login(
    client: TestClient,
    monkeypatch,
    intra_id: int = 42001,
    login: str = "Mario",
    display_name: str = "Mario Bros",
):
    monkeypatch.setenv("FT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("FT_CLIENT_SECRET", "test-client-secret")
    get_settings.cache_clear()

    monkeypatch.setattr(
        auth_service,
        "exchange_42_code_for_token",
        lambda code, redirect_uri: "fake-42-access-token",
    )
    monkeypatch.setattr(
        auth_service,
        "fetch_42_profile",
        lambda token: Intra42Profile(
            intra_id=intra_id,
            login=login,
            display_name=display_name,
        ),
    )

    auth_res = client.post(
        "/api/auth/oauth/42/authorize",
        json={"redirect_uri": REDIRECT_URI},
    )
    assert auth_res.status_code == 200
    url = auth_res.json()["authorization_url"]
    state = parse_qs(urlparse(url).query)["state"][0]

    return client.post(
        "/api/auth/oauth/42/callback",
        json={"code": "fake-code", "state": state, "redirect_uri": REDIRECT_URI},
    )


def test_oauth_42_creates_user_and_opens_session(client, monkeypatch):
    response = oauth_login(client, monkeypatch, intra_id=101, login="Mario", display_name="Mario Bros")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "mario"
    assert data["display_name"] == "Mario Bros"
    assert data["intra_id"] == 101
    assert COOKIE in client.cookies
    assert client.get("/api/auth/me").json()["username"] == "mario"


def test_oauth_42_existing_intra_id_logs_in_same_user(client, monkeypatch):
    first = oauth_login(client, monkeypatch, intra_id=101, login="mario", display_name="Mario")
    second = oauth_login(client, monkeypatch, intra_id=101, login="mario", display_name="Mario")

    assert first.json()["id"] == second.json()["id"]


def test_oauth_42_links_precreated_admin_account(client, db, monkeypatch):
    admin = create_user(db, "boss42", "boss42", is_admin=True)
    assert admin.intra_id is None

    response = oauth_login(client, monkeypatch, intra_id=999, login="boss42", display_name="Le Boss")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == admin.id
    assert body["is_admin"] is True
    assert body["intra_id"] == 999
    assert body["display_name"] == "Le Boss"


def test_oauth_42_rejects_invalid_state(client, monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("FT_CLIENT_SECRET", "test-client-secret")
    get_settings.cache_clear()

    client.post("/api/auth/oauth/42/authorize", json={"redirect_uri": REDIRECT_URI})
    response = client.post(
        "/api/auth/oauth/42/callback",
        json={"code": "fake-code", "state": "wrong-state", "redirect_uri": REDIRECT_URI},
    )
    assert response.status_code == 401


def test_oauth_42_rejects_disallowed_redirect_uri(client, monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "test-client-id")
    get_settings.cache_clear()

    response = client.post(
        "/api/auth/oauth/42/authorize",
        json={"redirect_uri": "https://evil.example.com/callback"},
    )
    assert response.status_code == 400


def test_me_requires_session(client):
    assert client.get("/api/auth/me").status_code == 401

    client.cookies.set(COOKIE, "jeton-invente")
    assert client.get("/api/auth/me").status_code == 401


def test_logout_invalidates_session_server_side(client, db, monkeypatch):
    oauth_login(client, monkeypatch)
    token = client.cookies[COOKIE]

    assert client.post("/api/auth/logout").status_code == 204
    assert db.scalars(select(AuthSession)).all() == []

    # Même si quelqu'un a gardé une copie du cookie, il n'est plus valable.
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401


def test_expired_session_is_rejected(client, db, monkeypatch):
    oauth_login(client, monkeypatch)
    db.execute(update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()

    assert client.get("/api/auth/me").status_code == 401


def test_session_token_is_not_stored_in_clear(client, db, monkeypatch):
    oauth_login(client, monkeypatch)

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
    player = create_user(db, "player", "Player")
    boss = create_user(db, "boss", "Boss", is_admin=True)

    lifetime = timedelta(days=1)
    player_token = auth_service.create_session(db, player, lifetime)
    boss_token = auth_service.create_session(db, boss, lifetime)

    with TestClient(test_app) as client:
        assert client.get("/admin-only").status_code == 401

        client.cookies.set(COOKIE, player_token)
        assert client.get("/admin-only").status_code == 403

        client.cookies.set(COOKIE, boss_token)
        assert client.get("/admin-only").status_code == 200
