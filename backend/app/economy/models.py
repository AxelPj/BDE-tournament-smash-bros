from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_column


class TransactionKind(StrEnum):
    ADMIN_ADJUSTMENT = "admin_adjustment"
    TOURNAMENT_REWARD = "tournament_reward"
    SHOP_PURCHASE = "shop_purchase"
    BET_STAKE = "bet_stake"
    BET_PAYOUT = "bet_payout"
    GAGE_REWARD = "gage_reward"


class TiltTransaction(Base):
    """Journal des mouvements de Tilt. Une ligne n'est jamais modifiée ni
    supprimée : une erreur se corrige par une transaction inverse."""

    __tablename__ = "tilt_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int]  # positif = gain, négatif = dépense
    balance_after: Mapped[int]
    kind: Mapped[TransactionKind] = mapped_column(enum_column(TransactionKind))
    description: Mapped[str] = mapped_column(String(255))
    # Clé unique optionnelle qui empêche de verser deux fois la même chose
    # (ex. "tournament:3:win:W1-2"). Une 2e transaction avec la même clé est ignorée.
    reference: Mapped[str | None] = mapped_column(String(100), unique=True)
    # Admin à l'origine du mouvement (None = attribué automatiquement par le serveur).
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
