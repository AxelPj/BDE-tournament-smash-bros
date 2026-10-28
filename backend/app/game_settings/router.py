from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.db import get_db
from app.game_settings.service import (
    MODE_LABELS,
    GameSettings,
    Mode,
    get_game_settings,
    is_enabled,
    update_game_settings,
)
from app.users.models import User

router = APIRouter(tags=["settings"])


def require_mode(mode: Mode):
    """À ajouter aux routes d'actions des joueurs :
    @router.post(..., dependencies=[require_mode(Mode.SHOP)])"""

    def check(db: Session = Depends(get_db)) -> None:
        if not is_enabled(db, mode):
            raise HTTPException(status.HTTP_403_FORBIDDEN, MODE_LABELS[mode])

    return Depends(check)


@router.get("/api/settings", response_model=GameSettings)
def read_settings(db: Session = Depends(get_db)):
    """Réglages globaux, dont les modes activés (pour masquer les boutons côté frontend)."""
    return get_game_settings(db)


@router.put("/api/admin/settings", response_model=GameSettings)
def write_settings(
    body: GameSettings, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    """Remplace tous les réglages (les champs omis reprennent leur valeur par défaut)."""
    return update_game_settings(db, body)


@router.patch("/api/admin/settings", response_model=GameSettings)
def patch_settings(
    body: dict[str, Any], db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    """Modifie seulement les réglages fournis. Ex. {"shop_enabled": false}"""
    unknown = body.keys() - GameSettings.model_fields.keys()
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Réglages inconnus : {sorted(unknown)}"
        )
    try:
        merged = GameSettings(**{**get_game_settings(db).model_dump(), **body})
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.errors(include_url=False))
    return update_game_settings(db, merged)
