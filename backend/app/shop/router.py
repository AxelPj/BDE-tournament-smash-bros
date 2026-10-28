from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.db import get_db
from app.economy.service import InsufficientFundsError
from app.game_settings.router import require_mode
from app.game_settings.service import Mode
from app.shop import service
from app.shop.models import Gage, InventoryStatus
from app.shop.schemas import GageCreate, GageRead, GageUpdate, InventoryItemRead
from app.users.models import User

router = APIRouter(tags=["shop"])


def _get_gage(gage_id: int, db: Session = Depends(get_db)) -> Gage:
    try:
        return service.get_gage(db, gage_id)
    except service.NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


# --- Joueurs ---


@router.get("/api/shop/gages", response_model=list[GageRead])
def shop(db: Session = Depends(get_db)):
    """Gages achetables (disponibles et non archivés), du moins cher au plus cher."""
    return service.list_gages(db, shop_only=True)


@router.post(
    "/api/shop/gages/{gage_id}/purchase",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_mode(Mode.SHOP)],
)
def purchase(
    gage_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return service.purchase(db, user.id, gage_id)
    except service.NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except (service.UnavailableError, InsufficientFundsError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/api/inventory", response_model=list[InventoryItemRead])
def my_inventory(
    status_filter: InventoryStatus | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gages du joueur connecté (les plus récents en premier), filtrables par statut."""
    return service.list_inventory(db, user.id, status_filter)


# --- Administration ---


@router.get("/api/admin/gages", response_model=list[GageRead])
def all_gages(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return service.list_gages(db, shop_only=False, include_archived=include_archived)


@router.post("/api/admin/gages", response_model=GageRead, status_code=status.HTTP_201_CREATED)
def create_gage(
    body: GageCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    return service.create_gage(db, **body.model_dump())


@router.patch("/api/admin/gages/{gage_id}", response_model=GageRead)
def update_gage(
    body: GageUpdate,
    gage: Gage = Depends(_get_gage),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Modifie un gage. Pour le supprimer, l'archiver (is_archived: true) :
    il disparaît de la boutique mais reste dans les inventaires et l'historique."""
    return service.update_gage(db, gage, **body.model_dump(exclude_unset=True))


@router.get("/api/admin/users/{user_id}/inventory", response_model=list[InventoryItemRead])
def user_inventory(
    user_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    return service.list_inventory(db, user_id)
