import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.models import AuthSession
from app.core.security import hash_password, verify_password
from app.users.models import User
from app.users.service import get_user_by_username

# Hash factice : on vérifie quand même un mot de passe quand l'utilisateur
# n'existe pas, pour que le temps de réponse ne révèle pas les comptes existants.
_DUMMY_HASH = hash_password("dummy-password")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None or user.password_hash is None:
        verify_password(_DUMMY_HASH, password)
        return None
    if not verify_password(user.password_hash, password):
        return None
    return user


def create_session(db: Session, user: User, lifetime: timedelta) -> str:
    """Crée une session et renvoie le jeton à placer dans le cookie."""
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=_hash_token(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + lifetime,
        )
    )
    db.commit()
    return token


def get_user_by_session(db: Session, token: str) -> User | None:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == _hash_token(token),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )
    return session.user if session else None


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
    db.commit()
