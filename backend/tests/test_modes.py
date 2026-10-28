"""Interrupteurs des modes de jeu (réglages globaux)."""

import pytest

from app.duels import service as duels
from app.shop import service as shop
from app.tournaments import service as tournaments
from app.users.service import create_user
from tests.test_scores import setup_tournament
from tests.test_tournaments_api import PASSWORD, login


@pytest.fixture
def ctx(client, db):
    """Un admin, deux joueurs, un tournoi généré, un duel validé, un gage en boutique."""
    admin_user = create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    mario = create_user(db, "mario", "Mario", PASSWORD)
    luigi = create_user(db, "luigi", "Luigi", PASSWORD)
    t, _ = setup_tournament(db, 2)
    open_t = tournaments.create_tournament(db, "Inscriptions ouvertes")
    duel = duels.create_duel(db, mario, luigi.id)
    duels.respond(db, duel, luigi, accept=True)
    duels.validate(db, duel, admin_user)
    gage = shop.create_gage(db, name="Kirby only", price=0)
    item = shop.purchase(db, mario.id, gage.id)
    return {
        "admin": login("admin"),
        "mario": login("mario"),
        "luigi": login("luigi"),
        "mario_id": mario.id,
        "luigi_id": luigi.id,
        "tournament": t,
        "open_tournament_id": open_t.id,
        "duel_id": duel.id,
        "gage_id": gage.id,
        "item_id": item.id,
    }


def disable(ctx, mode):
    response = ctx["admin"].patch("/api/admin/settings", json={f"{mode}_enabled": False})
    assert response.status_code == 200


def enable(ctx, mode):
    ctx["admin"].patch("/api/admin/settings", json={f"{mode}_enabled": True})


def test_all_modes_enabled_by_default(client):
    settings = client.get("/api/settings").json()
    assert all(settings[f"{m}_enabled"] for m in ["tournaments", "duels", "shop", "bets", "gages"])


def test_patch_changes_only_given_settings(ctx, client):
    disable(ctx, "shop")

    settings = client.get("/api/settings").json()
    assert settings["shop_enabled"] is False
    assert settings["duels_enabled"] is True
    assert settings["max_gages_per_player"] == 3

    admin = ctx["admin"]
    assert admin.patch("/api/admin/settings", json={"inconnu": 1}).status_code == 422
    assert admin.patch("/api/admin/settings", json={"max_gages_per_player": -1}).status_code == 422
    assert ctx["mario"].patch("/api/admin/settings", json={"shop_enabled": True}).status_code == 403


def test_tournaments_mode(ctx):
    url = f"/api/tournaments/{ctx['open_tournament_id']}/register"
    disable(ctx, "tournaments")

    response = ctx["mario"].post(url)
    assert response.status_code == 403
    assert "désactivées" in response.json()["detail"]
    # L'admin peut toujours inscrire des joueurs.
    admin_url = f"/api/tournaments/{ctx['open_tournament_id']}/participants"
    assert ctx["admin"].post(admin_url, json={"user_id": ctx["luigi_id"]}).status_code == 200

    enable(ctx, "tournaments")
    assert ctx["mario"].post(url).status_code == 204


def test_duels_mode(ctx):
    disable(ctx, "duels")

    assert ctx["luigi"].post("/api/duels", json={"opponent_id": ctx["mario_id"]}).status_code == 403
    # Le duel déjà validé continue : l'admin peut le lancer et saisir le résultat.
    duel_id = ctx["duel_id"]
    assert ctx["admin"].post(f"/api/admin/duels/{duel_id}/start").status_code == 200

    enable(ctx, "duels")


def test_duel_acceptance_blocked_but_refusal_allowed(ctx, db):
    create_user(db, "wario", "Wario", PASSWORD)
    wario = login("wario")
    first = wario.post("/api/duels", json={"opponent_id": ctx["mario_id"]}).json()["id"]
    disable(ctx, "duels")

    assert ctx["mario"].post(f"/api/duels/{first}/accept").status_code == 403
    assert ctx["mario"].post(f"/api/duels/{first}/refuse").status_code == 200


def test_shop_mode(ctx, client):
    url = f"/api/shop/gages/{ctx['gage_id']}/purchase"
    disable(ctx, "shop")

    response = ctx["mario"].post(url)
    assert response.status_code == 403
    assert response.json()["detail"] == "La boutique est fermée"
    assert client.get("/api/shop/gages").status_code == 200  # consultation possible
    assert ctx["admin"].post("/api/admin/gages", json={"name": "X", "price": 5}).status_code == 201

    enable(ctx, "shop")
    assert ctx["mario"].post(url).status_code == 201


def test_bets_mode(ctx):
    t = ctx["tournament"]
    body = {"picked_player_id": ctx["mario_id"], "amount": 1}
    disable(ctx, "bets")

    assert ctx["mario"].post(f"/api/duels/{ctx['duel_id']}/bets", json=body).status_code == 403
    match_body = {"picked_player_id": t.participants[0].user_id, "amount": 1}
    assert ctx["luigi"].post(f"/api/tournaments/{t.id}/matches/W1-1/bets", json=match_body).status_code == 403

    enable(ctx, "bets")
    # Mode rouvert : le pari passe le contrôle du mode et n'échoue que faute de solde (409).
    assert ctx["mario"].post(f"/api/duels/{ctx['duel_id']}/bets", json=body).status_code == 409


def test_gages_mode(ctx):
    url = f"/api/duels/{ctx['duel_id']}/gages"
    body = {"inventory_item_id": ctx["item_id"], "target_id": ctx["luigi_id"]}
    disable(ctx, "gages")

    assert ctx["mario"].post(url, json=body).status_code == 403

    enable(ctx, "gages")
    assert ctx["mario"].post(url, json=body).status_code == 201
