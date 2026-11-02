from dataclasses import dataclass
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.auth.models import AuthSession
from app.core.config import get_settings
from app.users.models import User


@dataclass(frozen=True)
class Intra42Profile:
    intra_id: int
    login: str
    display_name: str
    avatar_url: str | None = None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User, lifetime: timedelta) -> str:
    """Crée une session dans la table sessions et renvoie le jeton à placer dans le cookie."""
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
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(
            AuthSession.token_hash == _hash_token(token),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )
    return session.user if session else None


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
    db.commit()


# --- OAuth 42 ---


def validate_redirect_uri(redirect_uri: str) -> None:
    settings = get_settings()
    parsed = urlparse(redirect_uri)
    allowed_hosts = {
        h.strip() for h in settings.oauth_allowed_redirect_hosts.split(",") if h.strip()
    }
    is_local = parsed.hostname in {"localhost", "127.0.0.1"}

    if parsed.scheme != "https" and not (is_local and parsed.scheme == "http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri doit utiliser https hors développement local autorisé",
        )
    if not parsed.hostname or parsed.hostname not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri non autorisée",
        )


def build_42_authorization_url(redirect_uri: str) -> tuple[str, str]:
    """Vérifie la redirect_uri, génère un state anti-CSRF et construit l'URL OAuth 42.
    Retourne (authorization_url, state)."""
    settings = get_settings()
    if not settings.ft_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Variable d'environnement manquante: FT_CLIENT_ID",
        )
    validate_redirect_uri(redirect_uri)

    state = secrets.token_urlsafe(32)
    query = {
        "client_id": settings.ft_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "public",
        "state": state,
    }
    return f"{settings.ft_authorize_url}?{urlencode(query)}", state


def verify_oauth_state(state: str, cookie_state: str | None) -> None:
    if not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="State OAuth invalide ou expiré",
        )


def exchange_42_code_for_token(code: str, redirect_uri: str) -> str:
    """Échange le code d'autorisation renvoyé par 42 contre un access_token."""
    settings = get_settings()
    if not settings.ft_client_id or not settings.ft_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Variables d'environnement FT_CLIENT_ID / FT_CLIENT_SECRET manquantes",
        )

    data = {
        "client_id": settings.ft_client_id,
        "client_secret": settings.ft_client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    headers = {"Accept": "application/json"}

    try:
        response = httpx.post(settings.ft_token_url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Impossible d'échanger le code OAuth avec l'API 42",
        ) from exc

    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Réponse OAuth 42 sans access_token",
        )
    return str(access_token)


def fetch_42_profile(access_token: str) -> Intra42Profile:
    """Interroge /v2/me sur l'API 42 avec l'access_token et extrait le profil étudiant."""
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        response = httpx.get(settings.ft_userinfo_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Impossible de récupérer le profil sur l'API 42",
        ) from exc

    return parse_42_profile(data)


def parse_42_profile(data: dict[str, Any]) -> Intra42Profile:
    raw_id = data.get("id")
    login = str(data.get("login") or "").strip()
    if raw_id is None or not login:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Profil 42 incomplet (id ou login manquant)",
        )

    usual_full_name = str(data.get("usual_full_name") or "").strip()
    first_name = str(data.get("first_name") or "").strip()
    last_name = str(data.get("last_name") or "").strip()
    full_name = usual_full_name or f"{first_name} {last_name}".strip() or login

    image_obj = data.get("image") if isinstance(data.get("image"), dict) else {}
    versions = image_obj.get("versions") if isinstance(image_obj.get("versions"), dict) else {}
    avatar_url = versions.get("medium") or image_obj.get("link") or None

    return Intra42Profile(
        intra_id=int(raw_id),
        login=login,
        display_name=full_name,
        avatar_url=str(avatar_url) if avatar_url else None,
    )
