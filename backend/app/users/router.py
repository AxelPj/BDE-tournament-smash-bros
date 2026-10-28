from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.users.models import User
from app.users.schemas import UserPublic

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
def search_users(
    search: str = Query(default="", max_length=64),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Recherche de joueurs (ex. pour qu'un admin les ajoute à un tournoi)."""
    query = select(User).order_by(User.display_name).limit(50)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(User.username.ilike(pattern), User.display_name.ilike(pattern)))
    return db.scalars(query).all()
