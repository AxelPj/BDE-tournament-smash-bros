from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.db import get_db
from app.duels.models import Duel
from app.duels.router import _get_duel
from app.gages import service
from app.gages.models import GageUse, GageUseStatus
from app.gages.schemas import GageImpose, GageUseRead, GageValidation
from app.game_settings.router import require_mode
from app.game_settings.service import Mode
from app.tournaments.models import Tournament
from app.tournaments.router import _get_tournament
from app.users.models import User

router = APIRouter(tags=["gages"])


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except service.NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except service.ForbiddenError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    except service.GageStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


def _get_use(use_id: int, db: Session = Depends(get_db)) -> GageUse:
    with _http_errors():
        return service.get_use(db, use_id)


# --- Duels ---


@router.get("/api/duels/{duel_id}/gages", response_model=list[GageUseRead])
def duel_gages(duel: Duel = Depends(_get_duel), db: Session = Depends(get_db)):
    return service.list_uses(db, duel_id=duel.id)


@router.post(
    "/api/duels/{duel_id}/gages",
    response_model=GageUseRead,
    status_code=201,
    dependencies=[require_mode(Mode.GAGES)],
)
def impose_on_duel(
    body: GageImpose,
    duel: Duel = Depends(_get_duel),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Un joueur du duel impose un gage de son inventaire, avant le lancement."""
    with _http_errors():
        use = service.impose_on_duel(db, user, duel, body.inventory_item_id, body.target_id)
    return GageUseRead.model_validate(use)


# --- Matchs de tournoi ---


@router.get("/api/tournaments/{tournament_id}/matches/{code}/gages", response_model=list[GageUseRead])
def match_gages(
    code: str, tournament: Tournament = Depends(_get_tournament), db: Session = Depends(get_db)
):
    return service.list_uses(db, tournament_id=tournament.id, match_code=code)


@router.post(
    "/api/tournaments/{tournament_id}/matches/{code}/gages",
    response_model=GageUseRead,
    status_code=201,
    dependencies=[require_mode(Mode.GAGES)],
)
def impose_on_match(
    code: str,
    body: GageImpose,
    tournament: Tournament = Depends(_get_tournament),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Un joueur du match impose un gage de son inventaire, avant le lancement."""
    with _http_errors():
        use = service.impose_on_match(db, user, tournament, code, body.inventory_item_id, body.target_id)
    return GageUseRead.model_validate(use)


# --- Retrait et validation ---


@router.delete("/api/gage-uses/{use_id}", response_model=GageUseRead)
def withdraw(
    use: GageUse = Depends(_get_use),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Son auteur retire un gage imposé (avant le lancement) : il revient dans l'inventaire."""
    with _http_errors():
        return GageUseRead.model_validate(service.withdraw(db, use, user))


@router.get("/api/admin/gage-uses", response_model=list[GageUseRead])
def admin_list(
    status_filter: GageUseStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Ex. ?status=engaged : gages en attente de validation."""
    filters = {"status": status_filter} if status_filter else {}
    return service.list_uses(db, **filters)


@router.put("/api/admin/gage-uses/{use_id}/validation", response_model=GageUseRead)
def validate(
    body: GageValidation,
    use: GageUse = Depends(_get_use),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Indique si le gage a été réalisé (une fois le match lancé). Le gage est consommé.
    Une décision peut être corrigée."""
    with _http_errors():
        return GageUseRead.model_validate(service.validate(db, use, admin, body.completed))
