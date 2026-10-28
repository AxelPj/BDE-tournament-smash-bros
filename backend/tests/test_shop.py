import pytest
from sqlalchemy import select

from app.economy.models import TiltTransaction, TransactionKind
from app.economy.service import record_transaction
from app.shop.models import InventoryItem
from app.users.service import create_user
from tests.test_tournaments_api import PASSWORD, login

KIRBY = {"name": "Kirby only", "description": "Jouer uniquement Kirby", "price": 50}


@pytest.fixture
def accounts(client, db):
    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    player = create_user(db, "joueur", "Joueur", PASSWORD)
    record_transaction(db, player.id, 120, TransactionKind.ADMIN_ADJUSTMENT, "départ")
    db.commit()
    return login("admin"), login("joueur"), player


def create_gage(admin, **overrides):
    response = admin.post("/api/admin/gages", json={**KIRBY, **overrides})
    assert response.status_code == 201
    return response.json()


# --- Administration ---


def test_admin_manages_gages(accounts):
    admin, player, _ = accounts
    gage = create_gage(admin)
    assert gage["is_available"] and not gage["is_archived"]

    response = admin.patch(f"/api/admin/gages/{gage['id']}", json={"price": 80})
    assert response.json()["price"] == 80
    assert response.json()["name"] == "Kirby only"  # champ non fourni : inchangé

    assert player.post("/api/admin/gages", json=KIRBY).status_code == 403
    assert player.patch(f"/api/admin/gages/{gage['id']}", json={"price": 0}).status_code == 403
    assert admin.patch("/api/admin/gages/999", json={"price": 1}).status_code == 404


def test_gage_validation(accounts):
    admin, _, _ = accounts

    assert admin.post("/api/admin/gages", json={**KIRBY, "price": -1}).status_code == 422
    assert admin.post("/api/admin/gages", json={**KIRBY, "name": ""}).status_code == 422


def test_shop_lists_only_purchasable_gages(client, accounts):
    admin, _, _ = accounts
    visible = create_gage(admin, name="Visible")
    hidden = create_gage(admin, name="Désactivé", is_available=False)
    archived = create_gage(admin, name="Archivé")
    admin.patch(f"/api/admin/gages/{archived['id']}", json={"is_archived": True})

    assert [g["id"] for g in client.get("/api/shop/gages").json()] == [visible["id"]]
    admin_ids = {g["id"] for g in admin.get("/api/admin/gages").json()}
    assert admin_ids == {visible["id"], hidden["id"]}
    all_ids = {g["id"] for g in admin.get("/api/admin/gages?include_archived=true").json()}
    assert archived["id"] in all_ids


# --- Achat et inventaire ---


def test_purchase(accounts, db):
    admin, player, user = accounts
    gage = create_gage(admin)

    response = player.post(f"/api/shop/gages/{gage['id']}/purchase")

    assert response.status_code == 201
    item = response.json()
    assert (item["status"], item["purchase_price"], item["gage"]["name"]) == ("owned", 50, "Kirby only")
    assert player.get("/api/auth/me").json()["balance"] == 70
    history = player.get("/api/wallet/transactions").json()
    assert (history[0]["kind"], history[0]["amount"]) == ("shop_purchase", -50)
    assert db.get(InventoryItem, item["id"]).transaction_id == history[0]["id"]


def test_purchase_with_insufficient_funds_changes_nothing(accounts, db):
    admin, player, _ = accounts
    gage = create_gage(admin, price=121)

    assert player.post(f"/api/shop/gages/{gage['id']}/purchase").status_code == 409
    assert player.get("/api/auth/me").json()["balance"] == 120
    assert player.get("/api/inventory").json() == []


def test_cannot_buy_unavailable_or_archived_gages(accounts):
    admin, player, _ = accounts
    disabled = create_gage(admin, is_available=False)
    archived = create_gage(admin)
    admin.patch(f"/api/admin/gages/{archived['id']}", json={"is_archived": True})

    assert player.post(f"/api/shop/gages/{disabled['id']}/purchase").status_code == 409
    assert player.post(f"/api/shop/gages/{archived['id']}/purchase").status_code == 409
    assert player.post("/api/shop/gages/999/purchase").status_code == 404


def test_purchase_requires_login(client, accounts):
    admin, _, _ = accounts
    gage = create_gage(admin)

    assert client.post(f"/api/shop/gages/{gage['id']}/purchase").status_code == 401


def test_free_gage(accounts, db):
    admin, player, user = accounts
    gage = create_gage(admin, price=0)

    response = player.post(f"/api/shop/gages/{gage['id']}/purchase")

    assert response.status_code == 201
    assert player.get("/api/auth/me").json()["balance"] == 120
    purchases = db.scalars(
        select(TiltTransaction).where(TiltTransaction.kind == TransactionKind.SHOP_PURCHASE)
    ).all()
    assert purchases == []


def test_inventory_keeps_archived_gages(accounts):
    admin, player, user = accounts
    gage = create_gage(admin)
    player.post(f"/api/shop/gages/{gage['id']}/purchase")
    player.post(f"/api/shop/gages/{gage['id']}/purchase")  # 2 exemplaires

    admin.patch(f"/api/admin/gages/{gage['id']}", json={"is_archived": True})

    inventory = player.get("/api/inventory").json()
    assert len(inventory) == 2
    assert inventory[0]["gage"]["is_archived"] is True
    assert len(player.get("/api/inventory?status=owned").json()) == 2
    assert player.get("/api/inventory?status=consumed").json() == []
    assert len(admin.get(f"/api/admin/users/{user.id}/inventory").json()) == 2
    assert admin.get("/api/inventory").json() == []  # chacun ne voit que le sien


def test_purchase_is_all_or_nothing(accounts, db, monkeypatch):
    """Si l'ajout à l'inventaire échoue après le débit, le débit est annulé."""
    from app.shop import service

    admin, player, user = accounts
    gage = create_gage(admin)

    def broken_item(**_fields):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(service, "InventoryItem", broken_item)
    with pytest.raises(RuntimeError):
        service.purchase(db, user.id, gage["id"])
    db.rollback()  # ce que fait la fin de requête quand une erreur survient

    db.expire_all()
    assert user.balance == 120
    assert db.scalars(select(TiltTransaction).where(TiltTransaction.amount < 0)).all() == []
