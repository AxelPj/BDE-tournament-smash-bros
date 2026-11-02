from sqlalchemy.orm import sessionmaker

from app import cli
from app.users.service import create_user, get_user_by_username


def test_create_admin_creates_new_account(monkeypatch, engine, db):
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=engine))

    cli.create_admin("Admin", "Le Boss")

    user = get_user_by_username(db, "admin")
    assert user.is_admin
    assert user.display_name == "Le Boss"
    assert user.intra_id is None


def test_create_admin_promotes_existing_account(monkeypatch, engine, db):
    create_user(db, "peach", "Peach", intra_id=42)
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=engine))

    cli.create_admin("peach", None)

    db.expire_all()
    assert get_user_by_username(db, "peach").is_admin
