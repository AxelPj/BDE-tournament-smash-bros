from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_column


class Gage(Base):
    """Gage du catalogue (ex. « Jouer uniquement Kirby »), créé par les admins."""

    __tablename__ = "gages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(500), default="", server_default="")
    price: Mapped[int]
    # Visible et achetable dans la boutique (désactivable temporairement).
    is_available: Mapped[bool] = mapped_column(default=True, server_default="1")
    # Retiré définitivement de la boutique. Jamais supprimé, pour garder
    # l'historique des inventaires et des utilisations.
    is_archived: Mapped[bool] = mapped_column(default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InventoryStatus(StrEnum):
    OWNED = "owned"  # dans l'inventaire, pas encore utilisé
    ENGAGED = "engaged"  # imposé dans un match en cours
    CONSUMED = "consumed"  # utilisé


class InventoryItem(Base):
    """Un exemplaire de gage possédé par un joueur (un achat = une ligne)."""

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    gage_id: Mapped[int] = mapped_column(ForeignKey("gages.id"))
    status: Mapped[InventoryStatus] = mapped_column(
        enum_column(InventoryStatus), default=InventoryStatus.OWNED
    )
    purchase_price: Mapped[int]
    # Débit correspondant dans le journal des Tilt (None si le gage était gratuit).
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("tilt_transactions.id"))
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    gage: Mapped[Gage] = relationship()
