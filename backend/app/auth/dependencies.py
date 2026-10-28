"""Dépendances FastAPI à utiliser dans les routes protégées :

    def ma_route(user: User = Depends(get_current_user)): ...
    def route_admin(admin: User = Depends(require_admin)): ...
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.service import get_user_by_session
from app.core.config import get_settings
from app.core.db import get_db
from app.users.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    user = get_user_by_session(db, token) if token else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non connecté")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    # is_admin est relu en base à chaque requête : rien côté client ne peut le modifier.
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux administrateurs")
    return user
