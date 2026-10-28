from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    """Infos visibles par tous les joueurs connectés."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str


class UserRead(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    is_admin: bool
    intra_id: int | None
    balance: int
    created_at: datetime
