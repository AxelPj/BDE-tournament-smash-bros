import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, verify_password
from app.users.models import User


def make_user(username="mario", **kwargs):
    return User(username=username, display_name=username.title(), **kwargs)


def test_user_defaults(db):
    user = make_user()
    db.add(user)
    db.commit()

    assert user.id is not None
    assert user.is_admin is False
    assert user.created_at is not None
    assert user.password_hash is None
    assert user.intra_id is None


def test_username_is_unique(db):
    db.add(make_user("luigi"))
    db.commit()
    db.add(make_user("luigi"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_intra_id_is_unique_but_optional(db):
    # Plusieurs comptes locaux sans intra_id doivent coexister.
    db.add_all([make_user("peach"), make_user("daisy")])
    db.commit()

    db.add(make_user("yoshi", intra_id=42))
    db.commit()
    db.add(make_user("wario", intra_id=42))

    with pytest.raises(IntegrityError):
        db.commit()


def test_sqlite_pragmas_are_enabled(db):
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert db.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_password_hashing():
    hashed = hash_password("hadouken")

    assert hashed != "hadouken"
    assert verify_password(hashed, "hadouken")
    assert not verify_password(hashed, "shoryuken")
    assert not verify_password("pas-un-hash", "hadouken")
