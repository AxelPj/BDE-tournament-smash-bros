import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.users.service import create_user

PASSWORD = "password-123"


def login(username):
    """Nouveau client HTTP connecté (chaque client a ses propres cookies)."""
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return client


@pytest.fixture
def users(db):
    admin = create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    players = [create_user(db, f"player{i}", f"Player {i}", PASSWORD) for i in range(1, 6)]
    return admin, players


@pytest.fixture
def admin(client, users):
    return login("admin")


@pytest.fixture
def player(client, users):
    return login("player1")


@pytest.fixture
def tournament_id(admin):
    return admin.post("/api/tournaments", json={"name": "Smash BDE #1"}).json()["id"]


def participant_ids(client, tournament_id):
    return [p["user_id"] for p in client.get(f"/api/tournaments/{tournament_id}").json()["participants"]]


# --- Création et consultation ---


def test_only_admins_create_tournaments(client, admin, player):
    assert client.post("/api/tournaments", json={"name": "X"}).status_code == 401
    assert player.post("/api/tournaments", json={"name": "X"}).status_code == 403

    response = admin.post("/api/tournaments", json={"name": "Smash BDE #1"})
    assert response.status_code == 201
    assert response.json()["status"] == "registration"
    assert response.json()["registration_open"] is True


def test_tournaments_are_publicly_readable(client, tournament_id):
    assert client.get("/api/tournaments").json()[0]["id"] == tournament_id
    assert client.get(f"/api/tournaments/{tournament_id}").status_code == 200
    assert client.get("/api/tournaments/999").status_code == 404


# --- Inscriptions ---


def test_player_self_registration(player, tournament_id, users):
    _, players = users
    url = f"/api/tournaments/{tournament_id}/register"

    assert player.post(url).status_code == 204
    assert participant_ids(player, tournament_id) == [players[0].id]
    assert player.post(url).status_code == 409  # déjà inscrit

    assert player.delete(url).status_code == 204
    assert participant_ids(player, tournament_id) == []


def test_registration_requires_login(client, tournament_id):
    assert client.post(f"/api/tournaments/{tournament_id}/register").status_code == 401


def test_closed_registration_blocks_players_but_not_admins(admin, player, tournament_id, users):
    _, players = users
    admin.patch(f"/api/tournaments/{tournament_id}", json={"registration_open": False})

    assert player.post(f"/api/tournaments/{tournament_id}/register").status_code == 409

    response = admin.post(
        f"/api/tournaments/{tournament_id}/participants", json={"user_id": players[0].id}
    )
    assert response.status_code == 200
    assert player.delete(f"/api/tournaments/{tournament_id}/register").status_code == 409

    response = admin.delete(f"/api/tournaments/{tournament_id}/participants/{players[0].id}")
    assert response.status_code == 200
    assert response.json()["participants"] == []


def test_admin_participant_errors(admin, player, tournament_id, users):
    _, players = users
    url = f"/api/tournaments/{tournament_id}/participants"

    assert admin.post(url, json={"user_id": 999}).status_code == 404
    admin.post(url, json={"user_id": players[0].id})
    assert admin.post(url, json={"user_id": players[0].id}).status_code == 409
    assert admin.delete(f"{url}/{players[1].id}").status_code == 404
    assert player.post(url, json={"user_id": players[1].id}).status_code == 403


# --- Têtes de série et génération ---


def register_all(admin, tournament_id, players):
    for p in players:
        admin.post(f"/api/tournaments/{tournament_id}/participants", json={"user_id": p.id})


def test_set_seeds(admin, tournament_id, users):
    _, players = users
    register_all(admin, tournament_id, players)

    response = admin.put(
        f"/api/tournaments/{tournament_id}/seeds", json={"user_ids": [players[3].id, players[1].id]}
    )

    seeds = {p["user_id"]: p["seed"] for p in response.json()["participants"]}
    assert seeds[players[3].id] == 1
    assert seeds[players[1].id] == 2
    assert seeds[players[0].id] is None


def test_set_seeds_rejects_invalid_lists(admin, tournament_id, users):
    _, players = users
    register_all(admin, tournament_id, players[:2])
    url = f"/api/tournaments/{tournament_id}/seeds"

    assert admin.put(url, json={"user_ids": [players[0].id, players[0].id]}).status_code == 400
    assert admin.put(url, json={"user_ids": [players[4].id]}).status_code == 400


def test_generate_needs_two_participants(admin, tournament_id, users):
    _, players = users
    register_all(admin, tournament_id, players[:1])

    assert admin.post(f"/api/tournaments/{tournament_id}/generate").status_code == 409


def test_generate_bracket(admin, player, tournament_id, users):
    _, players = users
    register_all(admin, tournament_id, players)  # 5 joueurs -> bracket de 8 places
    admin.put(f"/api/tournaments/{tournament_id}/seeds", json={"user_ids": [players[4].id]})

    response = admin.post(f"/api/tournaments/{tournament_id}/generate")

    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 2 * 8 - 1  # WB 7 + LB 6 + GF + GF-R
    assert [m["code"] for m in matches[:2]] == ["W1-1", "W1-2"]
    assert matches[-1]["code"] == "GF-R"
    # La tête de série n°1 choisie par l'admin affronte un bye au premier tour.
    first = matches[0]
    assert first["player1_id"] == players[4].id
    assert first["is_bye"] and first["winner_id"] == players[4].id
    # Jouables : 4 contre 5 (W1-2) et 2 contre 3 (W2-2, tous deux qualifiés par un bye).
    assert [m["code"] for m in matches if m["status"] == "ready"] == ["W1-2", "W2-2"]

    detail = player.get(f"/api/tournaments/{tournament_id}").json()
    assert detail["status"] == "in_progress"
    assert detail["registration_open"] is False
    assert [p["bracket_seed"] for p in detail["participants"]] == [1, 2, 3, 4, 5]
    # La tête de série choisie par l'admin est conservée telle quelle.
    assert {p["user_id"]: p["seed"] for p in detail["participants"]}[players[4].id] == 1
    assert sum(p["seed"] is not None for p in detail["participants"]) == 1
    assert player.get(f"/api/tournaments/{tournament_id}/matches").json() == matches


def test_registration_frozen_after_generation(admin, player, tournament_id, users):
    _, players = users
    register_all(admin, tournament_id, players[1:4])
    admin.post(f"/api/tournaments/{tournament_id}/generate")

    assert player.post(f"/api/tournaments/{tournament_id}/register").status_code == 409
    response = admin.post(
        f"/api/tournaments/{tournament_id}/participants", json={"user_id": players[0].id}
    )
    assert response.status_code == 409
    assert admin.post(f"/api/tournaments/{tournament_id}/generate").status_code == 409
    assert admin.put(f"/api/tournaments/{tournament_id}/seeds", json={"user_ids": []}).status_code == 409


# --- Recherche de joueurs ---


def test_search_users(client, player):
    assert client.get("/api/users").status_code == 401

    results = player.get("/api/users", params={"search": "player 3"}).json()
    assert [u["username"] for u in results] == ["player3"]
    assert "is_admin" not in results[0]
