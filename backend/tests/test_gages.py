import pytest

from app.duels import service as duels
from app.gages import service as gages
from app.game_settings.service import GameSettings, update_game_settings
from app.shop import service as shop
from app.shop.models import InventoryStatus
from app.tournaments import service as tournaments
from app.users.models import User
from app.users.service import create_user
from tests.test_scores import setup_tournament, win
from tests.test_tournaments_api import PASSWORD, login


def balance(db, user_id):
    db.expire_all()
    return db.get(User, user_id).balance


def give_gages(db, user, count=1, **fields):
    """Ajoute des gages gratuits à l'inventaire d'un joueur (récompense 50 par défaut)."""
    gage = shop.create_gage(db, name="Kirby only", price=0, **fields)
    return [shop.purchase(db, user.id, gage.id) for _ in range(count)]


@pytest.fixture
def duel_setup(db):
    """Duel Mario (demandeur) contre Luigi, validé : gages et paris ouverts."""
    admin = create_user(db, "admin", "Admin", None, is_admin=True)
    mario = create_user(db, "mario", "Mario", None)
    luigi = create_user(db, "luigi", "Luigi", None)
    duel = duels.create_duel(db, mario, luigi.id)
    duels.respond(db, duel, luigi, accept=True)
    duels.validate(db, duel, admin)
    return duel, admin, mario, luigi


def finish(db, duel, challenger_wins=True):
    if duel.status.value == "validated":
        duels.start(db, duel)
    duels.report_result(db, duel, *((2, 0) if challenger_wins else (0, 2)))


# --- Imposer un gage ---


def test_impose_gage_on_opponent(db, duel_setup):
    duel, _, mario, luigi = duel_setup
    (item,) = give_gages(db, mario)

    use = gages.impose_on_duel(db, mario, duel, item.id, luigi.id)

    assert (use.status.value, use.target_id) == ("engaged", luigi.id)
    assert item.status is InventoryStatus.ENGAGED


def test_only_match_players_can_impose(db, duel_setup):
    duel, _, mario, luigi = duel_setup
    fan = create_user(db, "fan", "Fan", None)
    (fan_item,) = give_gages(db, fan)
    (item,) = give_gages(db, mario)

    with pytest.raises(gages.ForbiddenError):
        gages.impose_on_duel(db, fan, duel, fan_item.id, luigi.id)
    with pytest.raises(ValueError):
        gages.impose_on_duel(db, mario, duel, item.id, fan.id)  # cible hors du match
    with pytest.raises(gages.NotFoundError):
        gages.impose_on_duel(db, luigi, duel, item.id, mario.id)  # gage de Mario


def test_item_cannot_be_engaged_twice(db, duel_setup):
    duel, _, mario, luigi = duel_setup
    (item,) = give_gages(db, mario)
    gages.impose_on_duel(db, mario, duel, item.id, luigi.id)

    with pytest.raises(gages.GageStateError):
        gages.impose_on_duel(db, mario, duel, item.id, mario.id)


def test_limit_per_player_is_configurable(db, duel_setup):
    duel, _, mario, luigi = duel_setup
    items = give_gages(db, mario, 4)
    for item in items[:3]:
        gages.impose_on_duel(db, mario, duel, item.id, luigi.id)
    with pytest.raises(gages.GageStateError):
        gages.impose_on_duel(db, mario, duel, items[3].id, luigi.id)

    update_game_settings(db, GameSettings(max_gages_per_player=4))
    gages.impose_on_duel(db, mario, duel, items[3].id, mario.id)  # sur soi-même


def test_gages_only_before_start(db, duel_setup):
    duel, admin, mario, luigi = duel_setup
    item1, item2 = give_gages(db, mario, 2)
    pending = duels.create_duel(db, mario, create_user(db, "wario", "Wario", None).id)
    with pytest.raises(gages.GageStateError):
        gages.impose_on_duel(db, mario, pending, item1.id, mario.id)  # pas encore validé

    duels.start(db, duel)
    with pytest.raises(gages.GageStateError):
        gages.impose_on_duel(db, mario, duel, item2.id, luigi.id)


def test_withdraw(db, duel_setup):
    duel, _, mario, luigi = duel_setup
    item1, item2 = give_gages(db, mario, 2)
    use1 = gages.impose_on_duel(db, mario, duel, item1.id, luigi.id)
    use2 = gages.impose_on_duel(db, mario, duel, item2.id, luigi.id)

    with pytest.raises(gages.ForbiddenError):
        gages.withdraw(db, use1, luigi)
    gages.withdraw(db, use1, mario)
    assert (use1.status.value, item1.status) == ("cancelled", InventoryStatus.OWNED)

    duels.start(db, duel)
    with pytest.raises(gages.GageStateError):
        gages.withdraw(db, use2, mario)


# --- Validation et récompense ---


def test_validation_allowed_before_start(db, duel_setup):
    duel, admin, mario, luigi = duel_setup
    (item,) = give_gages(db, mario)
    use = gages.impose_on_duel(db, mario, duel, item.id, luigi.id)

    gages.validate(db, use, admin, completed=True)  # pas besoin que le match soit lancé

    assert item.status is InventoryStatus.CONSUMED
    assert item.used_at is not None


def test_validated_gage_rewards_its_user_whoever_wins(db, duel_setup):
    duel, admin, mario, luigi = duel_setup
    item1, item2 = give_gages(db, mario, 2)
    use1 = gages.impose_on_duel(db, mario, duel, item1.id, luigi.id)
    use2 = gages.impose_on_duel(db, mario, duel, item2.id, luigi.id)
    duels.start(db, duel)
    gages.validate(db, use1, admin, completed=True)
    gages.validate(db, use2, admin, completed=False)  # non respecté : pas de récompense

    finish(db, duel, challenger_wins=False)  # Mario perd : il touche quand même son objet

    assert balance(db, mario.id) == 50
    assert balance(db, luigi.id) == 0


def test_reward_is_set_per_gage(db, duel_setup):
    duel, admin, mario, luigi = duel_setup
    (item,) = give_gages(db, mario, reward=80)
    use = gages.impose_on_duel(db, mario, duel, item.id, luigi.id)

    gages.validate(db, use, admin, completed=True)

    assert balance(db, mario.id) == 80


def test_self_imposed_gage(db, duel_setup):
    duel, admin, mario, _ = duel_setup
    (item,) = give_gages(db, mario)
    use = gages.impose_on_duel(db, mario, duel, item.id, mario.id)
    duels.start(db, duel)
    gages.validate(db, use, admin, completed=True)

    finish(db, duel)

    assert balance(db, mario.id) == 50


def test_reward_follows_validation_not_result(db, duel_setup):
    duel, admin, mario, luigi = duel_setup
    (item,) = give_gages(db, mario)
    use = gages.impose_on_duel(db, mario, duel, item.id, luigi.id)
    duels.start(db, duel)
    gages.validate(db, use, admin, completed=True)
    finish(db, duel, challenger_wins=False)
    assert balance(db, mario.id) == 50

    finish(db, duel, challenger_wins=True)  # correction du résultat : sans effet
    assert balance(db, mario.id) == 50

    gages.validate(db, use, admin, completed=False)  # correction de la validation
    assert balance(db, mario.id) == 0


def test_cancelled_duel_returns_engaged_gages(db, duel_setup):
    duel, admin, mario, luigi = duel_setup
    item1, item2 = give_gages(db, mario, 2)
    use1 = gages.impose_on_duel(db, mario, duel, item1.id, luigi.id)
    gages.impose_on_duel(db, mario, duel, item2.id, luigi.id)
    duels.start(db, duel)
    gages.validate(db, use1, admin, completed=True)

    duels.cancel(db, duel, admin)

    assert item1.status is InventoryStatus.CONSUMED  # réellement joué
    assert item2.status is InventoryStatus.OWNED  # rendu


# --- Matchs de tournoi ---


def test_tournament_gage_reward_and_corrections(db):
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)  # W1-1 = p0 contre p3
    admin = create_user(db, "admin", "Admin", None, is_admin=True)
    user0 = db.get(User, p0)
    (item,) = give_gages(db, user0)
    use = gages.impose_on_match(db, user0, t, "W1-1", item.id, p3)
    tournaments.start_match(db, t, "W1-1")
    gages.validate(db, use, admin, completed=True)
    before0, before3 = balance(db, p0), balance(db, p3)
    assert before0 == 100 + 50  # participation + objet validé

    win(db, t, "W1-1", first_player_wins=False)  # p3 gagne
    assert balance(db, p0) == before0 + 10  # p0 garde la récompense de son objet
    assert balance(db, p3) == before3 + 10 + 20

    win(db, t, "W1-1")  # correction : p0 a gagné
    assert balance(db, p0) == before0 + 10 + 20
    assert balance(db, p3) == before3 + 10

    gages.validate(db, use, admin, completed=False)
    assert balance(db, p0) == before0 - 50 + 10 + 20


def test_tournament_pairing_change_returns_engaged_gage(db):
    t, (p0, p1, p2, p3) = setup_tournament(db, 4)
    win(db, t, "W1-1")
    win(db, t, "W1-2")
    user0 = db.get(User, p0)
    (item,) = give_gages(db, user0)
    use = gages.impose_on_match(db, user0, t, "W2-1", item.id, p1)  # p0 contre p1

    win(db, t, "W1-1", first_player_wins=False)  # W2-1 devient p3 contre p1

    assert use.status.value == "cancelled"
    assert item.status is InventoryStatus.OWNED


def test_reset_bracket_returns_engaged_gages(db):
    t, (p0, *_) = setup_tournament(db, 4)
    user0 = db.get(User, p0)
    (item,) = give_gages(db, user0)
    gages.impose_on_match(db, user0, t, "W1-1", item.id, p0)

    tournaments.reset_bracket(db, t)

    assert item.status is InventoryStatus.OWNED


# --- API ---


def test_api_settings(client, db):
    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    create_user(db, "joueur", "Joueur", PASSWORD)
    admin, player = login("admin"), login("joueur")

    def gage_settings(data):
        return {k: data[k] for k in ("max_gages_per_player", "duel_gage_win_reward")}

    assert gage_settings(client.get("/api/settings").json()) == {
        "max_gages_per_player": 3,
        "duel_gage_win_reward": 50,
    }
    new = {"max_gages_per_player": 2, "duel_gage_win_reward": 80}
    assert player.put("/api/admin/settings", json=new).status_code == 403
    assert gage_settings(admin.put("/api/admin/settings", json=new).json()) == new
    assert gage_settings(client.get("/api/settings").json()) == new
    assert admin.put("/api/admin/settings", json={"max_gages_per_player": -1}).status_code == 422


def test_api_gage_flow(client, db):
    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    mario = create_user(db, "mario", "Mario", PASSWORD)
    luigi = create_user(db, "luigi", "Luigi", PASSWORD)
    (item,) = give_gages(db, mario)
    admin, mario_c, luigi_c = login("admin"), login("mario"), login("luigi")
    duel_id = mario_c.post("/api/duels", json={"opponent_id": luigi.id}).json()["id"]
    luigi_c.post(f"/api/duels/{duel_id}/accept")
    admin.post(f"/api/admin/duels/{duel_id}/validate")

    body = {"inventory_item_id": item.id, "target_id": luigi.id}
    response = mario_c.post(f"/api/duels/{duel_id}/gages", json=body)
    assert response.status_code == 201
    use = response.json()
    assert use["gage"]["name"] == "Kirby only"
    assert luigi_c.post(f"/api/duels/{duel_id}/gages", json=body).status_code == 404
    assert [u["id"] for u in client.get(f"/api/duels/{duel_id}/gages").json()] == [use["id"]]
    assert [u["id"] for u in admin.get("/api/admin/gage-uses?status=engaged").json()] == [use["id"]]

    url = f"/api/admin/gage-uses/{use['id']}/validation"
    admin.post(f"/api/admin/duels/{duel_id}/start")
    assert mario_c.put(url, json={"completed": True}).status_code == 403
    assert admin.put(url, json={"completed": True}).json()["status"] == "completed"
    admin.put(f"/api/admin/duels/{duel_id}/result", json={"challenger_score": 0, "opponent_score": 2})

    assert mario_c.get("/api/auth/me").json()["balance"] == 50  # celui qui a utilisé l'objet
    assert luigi_c.get("/api/auth/me").json()["balance"] == 0
    assert mario_c.get("/api/inventory").json()[0]["status"] == "consumed"
