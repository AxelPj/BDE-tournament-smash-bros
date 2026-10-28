from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.auth.dependencies import get_current_user, require_admin
from app.core.db import get_db
from app.duels import service
from app.duels.models import Duel, DuelStatus
from app.duels.schemas import DuelCreate, DuelRead, DuelResult
from app.game_settings.router import require_mode
from app.game_settings.service import Mode
from app.users.models import User

router = APIRouter(tags=["duels"])


@contextmanager
def _http_errors() -> Iterator[None]:
    """Traduit les erreurs métier en réponses HTTP."""
    try:
        yield
    except service.NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except service.ForbiddenError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    except service.DuelStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except StaleDataError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Le duel a été modifié en même temps par quelqu'un d'autre : rechargez et réessayez",
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


def _get_duel(duel_id: int, db: Session = Depends(get_db)) -> Duel:
    with _http_errors():
        return service.get_duel(db, duel_id)


# --- Consultation ---


@router.get("/api/duels", response_model=list[DuelRead])
def list_duels(
    status_filter: DuelStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    """Tous les duels (200 plus récents), filtrables par statut.
    Ex. ?status=accepted : duels en attente de validation par un admin."""
    return service.list_duels(db, status_filter)


@router.get("/api/duels/mine", response_model=list[DuelRead])
def my_duels(
    status_filter: DuelStatus | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Duels du joueur connecté. Ex. ?status=pending : défis en attente de réponse
    (à interroger régulièrement par le frontend pour afficher les notifications)."""
    return service.list_duels(db, status_filter, user_id=user.id)


@router.get("/api/duels/{duel_id}", response_model=DuelRead)
def get_duel(duel: Duel = Depends(_get_duel)):
    return duel


# --- Joueurs ---


@router.post(
    "/api/duels",
    response_model=DuelRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_mode(Mode.DUELS)],
)
def create_duel(
    body: DuelCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    with _http_errors():
        return service.create_duel(db, user, body.opponent_id)


@router.post(
    "/api/duels/{duel_id}/accept",
    response_model=DuelRead,
    dependencies=[require_mode(Mode.DUELS)],
)
def accept(
    duel: Duel = Depends(_get_duel),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with _http_errors():
        return service.respond(db, duel, user, accept=True)


@router.post("/api/duels/{duel_id}/refuse", response_model=DuelRead)
def refuse(
    duel: Duel = Depends(_get_duel),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with _http_errors():
        return service.respond(db, duel, user, accept=False)


@router.post("/api/duels/{duel_id}/cancel", response_model=DuelRead)
def cancel(
    duel: Duel = Depends(_get_duel),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Demandeur : tant que le défi n'est pas accepté. Admin : à tout moment avant la fin."""
    with _http_errors():
        return service.cancel(db, duel, user)


# --- Administration ---


@router.post("/api/admin/duels/{duel_id}/validate", response_model=DuelRead)
def validate(
    duel: Duel = Depends(_get_duel),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    with _http_errors():
        return service.validate(db, duel, admin)


@router.post("/api/admin/duels/{duel_id}/start", response_model=DuelRead)
def start(
    duel: Duel = Depends(_get_duel),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    with _http_errors():
        return service.start(db, duel)


@router.put("/api/admin/duels/{duel_id}/result", response_model=DuelRead)
def report_result(
    body: DuelResult,
    duel: Duel = Depends(_get_duel),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Saisit le score d'un duel en cours, ou corrige celui d'un duel terminé."""
    with _http_errors():
        return service.report_result(db, duel, body.challenger_score, body.opponent_score)
