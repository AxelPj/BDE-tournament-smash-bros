from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_column
from app.shop.models import Gage, InventoryItem


class GageUseStatus(StrEnum):
    ENGAGED = "engaged"  # imposé, en attente du match puis de la validation
    COMPLETED = "completed"  # réalisé (validé par un admin)
    FAILED = "failed"  # non réalisé (validé par un admin)
    CANCELLED = "cancelled"  # retiré ou match annulé : le gage revient dans l'inventaire


class GageUse(Base):
    """Un gage de l'inventaire imposé par un joueur à lui-même ou à son
    adversaire, dans un duel OU un match de tournoi (désigné comme pour les paris)."""

    __tablename__ = "gage_uses"
    __table_args__ = (
        CheckConstraint(
            "(duel_id IS NOT NULL AND tournament_id IS NULL AND match_code IS NULL)"
            " OR (duel_id IS NULL AND tournament_id IS NOT NULL AND match_code IS NOT NULL)",
            name="single_target",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    imposer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Adversaire de celui qui impose : avec imposer_id, il identifie l'affiche du match.
    other_player_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    duel_id: Mapped[int | None] = mapped_column(ForeignKey("duels.id"), index=True)
    tournament_id: Mapped[int | None] = mapped_column(ForeignKey("tournaments.id"), index=True)
    match_code: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[GageUseStatus] = mapped_column(
        enum_column(GageUseStatus), default=GageUseStatus.ENGAGED
    )
    validated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    item: Mapped[InventoryItem] = relationship()

    @property
    def gage(self) -> Gage:
        return self.item.gage
