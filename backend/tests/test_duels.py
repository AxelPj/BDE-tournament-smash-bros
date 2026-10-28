import pytest
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.duels import service
from app.duels.models import Duel
from app.users.service import create_user
from tests.test_tournaments_api import PASSWORD, login


@pytest.fixture
def accounts(client, db):
    create_user(db, "admin", "Admin", PASSWORD, is_admin=True)
    mario = create_user(db, "mario", "Mario", PASSWORD)
    luigi = create_user(db, "luigi", "Luigi", PASSWORD)
    create_user(db, "wario", "Wario", PASSWORD)
    return {
        "admin": login("admin"),
        "mario": login("mario"),
        "luigi": login("luigi"),
        "wario": login("wario"),
        "mario_id": mario.id,
        "luigi_id": luigi.id,
    }


def challenge(a):
    """Mario défie Luigi."""
    response = a["mario"].post("/api/duels", json={"opponent_id": a["luigi_id"]})
    assert response.status_code == 201
    return response.json()["id"]


def test_full_duel_flow(accounts):
    a = accounts
    duel_id = challenge(a)
    assert a["luigi"].get("/api/duels/mine?status=pending").json()[0]["id"] == duel_id

    assert a["luigi"].post(f"/api/duels/{duel_id}/accept").json()["status"] == "accepted"
    assert a["admin"].get("/api/duels?status=accepted").json()[0]["id"] == duel_id
    assert a["admin"].post(f"/api/admin/duels/{duel_id}/validate").json()["status"] == "validated"
    assert a["admin"].post(f"/api/admin/duels/{duel_id}/start").json()["status"] == "in_progress"

    response = a["admin"].put(
        f"/api/admin/duels/{duel_id}/result", json={"challenger_score": 1, "opponent_score": 3}
    )
    duel = response.json()
    assert duel["status"] == "completed"
    assert duel["winner_id"] == a["luigi_id"]
    assert duel["challenger"]["username"] == "mario"


def test_duels_give_no_tilt(accounts):
    a = accounts
    duel_id = challenge(a)
    a["luigi"].post(f"/api/duels/{duel_id}/accept")
    a["admin"].post(f"/api/admin/duels/{duel_id}/validate")
    a["admin"].post(f"/api/admin/duels/{duel_id}/start")
    a["admin"].put(f"/api/admin/duels/{duel_id}/result", json={"challenger_score": 2, "opponent_score": 0})

    assert a["mario"].get("/api/auth/me").json()["balance"] == 0
    assert a["luigi"].get("/api/auth/me").json()["balance"] == 0


def test_result_can_be_corrected(accounts):
    a = accounts
    duel_id = challenge(a)
    a["luigi"].post(f"/api/duels/{duel_id}/accept")
    a["admin"].post(f"/api/admin/duels/{duel_id}/validate")
    a["admin"].post(f"/api/admin/duels/{duel_id}/start")
    url = f"/api/admin/duels/{duel_id}/result"
    a["admin"].put(url, json={"challenger_score": 2, "opponent_score": 0})

    corrected = a["admin"].put(url, json={"challenger_score": 0, "opponent_score": 2}).json()

    assert corrected["winner_id"] == a["luigi_id"]


def test_refuse(accounts):
    a = accounts
    duel_id = challenge(a)

    assert a["mario"].post(f"/api/duels/{duel_id}/refuse").status_code == 403  # pas le défié
    assert a["luigi"].post(f"/api/duels/{duel_id}/refuse").json()["status"] == "refused"
    assert a["luigi"].post(f"/api/duels/{duel_id}/accept").status_code == 409


def test_cancel_rules(accounts):
    a = accounts
    duel_id = challenge(a)
    assert a["wario"].post(f"/api/duels/{duel_id}/cancel").status_code == 403
    assert a["luigi"].post(f"/api/duels/{duel_id}/cancel").status_code == 403

    a["luigi"].post(f"/api/duels/{duel_id}/accept")
    # Une fois accepté, seul un admin peut annuler.
    assert a["mario"].post(f"/api/duels/{duel_id}/cancel").status_code == 409
    a["admin"].post(f"/api/admin/duels/{duel_id}/validate")
    a["admin"].post(f"/api/admin/duels/{duel_id}/start")
    assert a["admin"].post(f"/api/duels/{duel_id}/cancel").json()["status"] == "cancelled"
    assert a["admin"].post(f"/api/duels/{duel_id}/cancel").status_code == 409


def test_challenger_can_cancel_pending(accounts):
    a = accounts
    duel_id = challenge(a)

    assert a["mario"].post(f"/api/duels/{duel_id}/cancel").json()["status"] == "cancelled"


def test_invalid_challenges(accounts, client):
    a = accounts
    assert a["mario"].post("/api/duels", json={"opponent_id": a["mario_id"]}).status_code == 400
    assert a["mario"].post("/api/duels", json={"opponent_id": 999}).status_code == 404
    assert client.post("/api/duels", json={"opponent_id": a["luigi_id"]}).status_code == 401

    challenge(a)
    # Un seul duel actif par paire, dans un sens comme dans l'autre.
    assert a["mario"].post("/api/duels", json={"opponent_id": a["luigi_id"]}).status_code == 409
    assert a["luigi"].post("/api/duels", json={"opponent_id": a["mario_id"]}).status_code == 409


def test_new_duel_allowed_after_previous_one_ends(accounts):
    a = accounts
    duel_id = challenge(a)
    a["luigi"].post(f"/api/duels/{duel_id}/refuse")

    challenge(a)


def test_admin_steps_require_admin_and_right_order(accounts):
    a = accounts
    duel_id = challenge(a)
    result = {"challenger_score": 2, "opponent_score": 0}

    assert a["mario"].post(f"/api/admin/duels/{duel_id}/validate").status_code == 403
    assert a["admin"].post(f"/api/admin/duels/{duel_id}/validate").status_code == 409  # pas accepté
    a["luigi"].post(f"/api/duels/{duel_id}/accept")
    assert a["admin"].post(f"/api/admin/duels/{duel_id}/start").status_code == 409  # pas validé
    assert a["admin"].put(f"/api/admin/duels/{duel_id}/result", json=result).status_code == 409
    a["admin"].post(f"/api/admin/duels/{duel_id}/validate")
    a["admin"].post(f"/api/admin/duels/{duel_id}/start")
    draw = {"challenger_score": 1, "opponent_score": 1}
    assert a["admin"].put(f"/api/admin/duels/{duel_id}/result", json=draw).status_code == 400
    assert a["admin"].get("/api/duels/999").status_code == 404


def test_concurrent_changes_are_rejected(engine, db):
    mario = create_user(db, "m", "M", None)
    luigi = create_user(db, "l", "L", None)
    duel = service.create_duel(db, mario, luigi.id)

    with Session(engine) as first, Session(engine) as second:
        d1, d2 = first.get(Duel, duel.id), second.get(Duel, duel.id)
        service.respond(first, d1, first.get(type(luigi), luigi.id), accept=True)
        with pytest.raises(StaleDataError):
            service.cancel(second, d2, second.get(type(mario), mario.id))
