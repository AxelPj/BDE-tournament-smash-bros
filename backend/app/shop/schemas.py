from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.shop.models import InventoryStatus


class GageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    price: int = Field(ge=0, le=100_000, description="Prix en Tilt")
    is_available: bool = True


class GageUpdate(BaseModel):
    """Seuls les champs fournis sont modifiés."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    price: int | None = Field(default=None, ge=0, le=100_000)
    is_available: bool | None = None
    is_archived: bool | None = None


class GageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: int
    is_available: bool
    is_archived: bool


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gage: GageRead
    status: InventoryStatus
    purchase_price: int
    purchased_at: datetime
    used_at: datetime | None
