from sqlalchemy.orm import sessionmaker

from app import cli
from app.core.security import verify_password
from app.users.service import create_user, get_user_by_username


def test_create_admin_creates_new_account(monkeypatch, engine, db):
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: "super-secret")

    cli.create_admin("Admin", "Le Boss")

    user = get_user_by_username(db, "admin")
    assert user.is_admin
    assert user.display_name == "Le Boss"
    assert verify_password(user.password_hash, "super-secret")


def test_create_admin_promotes_existing_account(monkeypatch, engine, db):
    create_user(db, "peach", "Peach", "princess-1")
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=engine))

    cli.create_admin("peach", None)

    db.expire_all()
    assert get_user_by_username(db, "peach").is_admin
