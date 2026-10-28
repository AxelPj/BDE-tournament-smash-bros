from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, RegisterRequest
from app.core.config import get_settings
from app.core.db import get_db
from app.users.models import User
from app.users.schemas import UserRead
from app.users.service import UsernameTakenError, create_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _open_session(response: Response, db: Session, user: User) -> None:
    settings = get_settings()
    lifetime = timedelta(days=settings.session_lifetime_days)
    token = service.create_session(db, user, lifetime)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,  # inaccessible au JavaScript de la page
        secure=settings.cookie_secure,
        samesite="lax",  # non envoyé par les requêtes POST d'autres sites
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Crée un compte local et connecte directement l'utilisateur."""
    try:
        user = create_user(db, body.username, body.display_name, body.password)
    except UsernameTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nom d'utilisateur déjà pris")
    _open_session(response, db, user)
    return user


@router.post("/login", response_model=UserRead)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = service.authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    _open_session(response, db, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        service.delete_session(db, token)
    response.delete_cookie(settings.session_cookie_name)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
