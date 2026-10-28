from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.gages.models import GageUseStatus
from app.shop.schemas import GageRead


class GageImpose(BaseModel):
    inventory_item_id: int = Field(description="Exemplaire de ton inventaire (statut owned)")
    target_id: int = Field(description="Joueur du match qui subit le gage (toi ou ton adversaire)")


class GageValidation(BaseModel):
    completed: bool = Field(description="true : le gage a été réalisé ; false : non réalisé")


class GageUseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    imposer_id: int
    target_id: int
    duel_id: int | None
    tournament_id: int | None
    match_code: str | None
    status: GageUseStatus
    gage: GageRead
    validated_at: datetime | None
    created_at: datetime
