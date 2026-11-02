from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserAvatarUpdate(BaseModel):
    avatar_url: str = Field(min_length=1, max_length=500)


class UserPublic(BaseModel):
    """Infos visibles par tous les joueurs connectés."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    avatar_url: str | None = None


class UserRead(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    is_admin: bool
    intra_id: int | None
    balance: int
    created_at: datetime


class UserStatsRead(BaseModel):
    id: int | None = None
    login: str
    display_name: str
    avatar_url: str | None = None
    is_admin: bool = False
    campus: str
    wins: int
    losses: int
    tournaments: int
    rank: int
    balance: int
