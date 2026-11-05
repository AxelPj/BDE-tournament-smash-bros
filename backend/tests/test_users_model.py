import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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
    assert user.intra_id is None


def test_username_is_unique(db):
    db.add(make_user("luigi"))
    db.commit()
    db.add(make_user("luigi"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_intra_id_is_unique_but_optional(db):
    # Plusieurs comptes sans intra_id doivent coexister.
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


def test_42_login_keeps_chosen_fighter_avatar(db):
    """Le combattant choisi comme photo de profil n'est pas écrasé à la reconnexion 42."""
    from app.users.service import get_or_create_42_user

    user = get_or_create_42_user(db, 4242, "peach", "Peach", "https://cdn.intra.42.fr/a.jpg")
    user.avatar_url = "/fighters/peach.png"
    db.commit()

    again = get_or_create_42_user(db, 4242, "peach", "Peach", "https://cdn.intra.42.fr/b.jpg")
    assert again.avatar_url == "/fighters/peach.png"


def test_first_42_login_grants_welcome_bonus_once(db):
    from app.economy.models import TiltTransaction, TransactionKind
    from app.users.service import get_or_create_42_user

    user = get_or_create_42_user(db, 4242, "peach", "Peach")
    assert user.balance == 100
    assert db.query(TiltTransaction).filter_by(
        user_id=user.id, kind=TransactionKind.WELCOME_BONUS
    ).count() == 1

    again = get_or_create_42_user(db, 4242, "peach", "Peach")
    assert again.balance == 100
    assert db.query(TiltTransaction).filter_by(
        user_id=user.id, kind=TransactionKind.WELCOME_BONUS
    ).count() == 1


def test_42_login_refreshes_intra_photo(db):
    """Sans combattant choisi, la photo 42 suit celle de l'intra."""
    from app.users.service import get_or_create_42_user

    get_or_create_42_user(db, 4343, "toad", "Toad", "https://cdn.intra.42.fr/a.jpg")
    again = get_or_create_42_user(db, 4343, "toad", "Toad", "https://cdn.intra.42.fr/b.jpg")
    assert again.avatar_url == "https://cdn.intra.42.fr/b.jpg"
