from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.duels.models import DuelStatus
from app.users.schemas import UserPublic


class DuelCreate(BaseModel):
    opponent_id: int


class DuelResult(BaseModel):
    challenger_score: int = Field(ge=0, le=99)
    opponent_score: int = Field(ge=0, le=99)


class DuelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    challenger: UserPublic
    opponent: UserPublic
    status: DuelStatus
    challenger_score: int | None
    opponent_score: int | None
    winner_id: int | None
    created_at: datetime
    responded_at: datetime | None
    validated_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    betting_open: bool = Field(description="Paris acceptés (duel validé, pas encore lancé)")
