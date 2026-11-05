from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.users.models import User
from app.users.schemas import UserRead
from app.users.service import get_or_create_42_user

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


@router.post("/oauth/42/authorize", response_model=OAuthAuthorizeResponse)
def oauth_42_authorize(body: OAuthAuthorizeRequest, response: Response):
    """Prépare la redirection vers l'intra 42 et pose le cookie de state anti-CSRF."""
    settings = get_settings()
    authorization_url, state = service.build_42_authorization_url(body.redirect_uri)
    response.set_cookie(
        settings.oauth_state_cookie_name,
        state,
        max_age=settings.oauth_state_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        # Le retour OAuth vient d'un autre site (42). En HTTPS, None évite
        # que les protections anti-pistage mobiles suppriment le state.
        samesite="none" if settings.cookie_secure else "lax",
    )
    return OAuthAuthorizeResponse(authorization_url=authorization_url)


@router.post("/oauth/42/callback", response_model=UserRead)
def oauth_42_callback(
    body: OAuthCallbackRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Vérifie le retour OAuth de 42, inscrit ou récupère l'étudiant dans `users`,
    et ouvre une session dans la table `sessions`."""
    settings = get_settings()
    service.validate_redirect_uri(body.redirect_uri)

    cookie_state = request.cookies.get(settings.oauth_state_cookie_name)
    response.delete_cookie(settings.oauth_state_cookie_name)
    service.verify_oauth_state(body.state, cookie_state)

    access_token = service.exchange_42_code_for_token(body.code, body.redirect_uri)
    profile = service.fetch_42_profile(access_token)
    user = get_or_create_42_user(
        db,
        intra_id=profile.intra_id,
        login=profile.login,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
    )
    _open_session(response, db, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        service.delete_session(db, token)
    # Mêmes options qu'à la création, sinon le navigateur peut garder le cookie (HTTPS).
    response.delete_cookie(
        settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
