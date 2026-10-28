from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.db import get_db
from app.economy import service
from app.economy.models import TransactionKind
from app.economy.schemas import AdminAdjustment, TransactionRead
from app.users.models import User

router = APIRouter(tags=["tilt"])


@router.get("/api/wallet/transactions", response_model=list[TransactionRead])
def my_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historique des Tilt du joueur connecté (le plus récent en premier).
    Le solde est dans GET /api/auth/me."""
    return service.list_transactions(db, user.id, limit, offset)


@router.get("/api/admin/users/{user_id}/transactions", response_model=list[TransactionRead])
def user_transactions(
    user_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return service.list_transactions(db, user_id, limit, offset)


@router.post(
    "/api/admin/users/{user_id}/tilt",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def adjust_balance(
    user_id: int,
    body: AdminAdjustment,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Donne (montant positif) ou retire (montant négatif) des Tilt à un joueur."""
    try:
        transaction = service.record_transaction(
            db,
            user_id,
            body.amount,
            TransactionKind.ADMIN_ADJUSTMENT,
            body.reason.strip(),
            created_by_id=admin.id,
        )
    except service.UnknownUserError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except service.InsufficientFundsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    db.commit()
    return transaction
