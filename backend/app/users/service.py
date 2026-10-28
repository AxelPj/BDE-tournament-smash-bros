from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.users.models import User


class UsernameTakenError(Exception):
    pass


def normalize_username(username: str) -> str:
    """Les identifiants sont insensibles à la casse : "Mario" == "mario"."""
    return username.strip().lower()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == normalize_username(username)))


def create_user(
    db: Session,
    username: str,
    display_name: str,
    password: str | None,
    is_admin: bool = False,
) -> User:
    user = User(
        username=normalize_username(username),
        display_name=display_name.strip(),
        password_hash=hash_password(password) if password else None,
        is_admin=is_admin,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UsernameTakenError(user.username) from exc
    return user
