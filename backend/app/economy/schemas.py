from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.economy.models import TransactionKind


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    balance_after: int
    kind: TransactionKind
    description: str
    created_by_id: int | None
    created_at: datetime


class AdminAdjustment(BaseModel):
    amount: int = Field(
        ge=-100_000, le=100_000, description="Positif pour donner, négatif pour retirer"
    )
    reason: str = Field(min_length=1, max_length=200)
