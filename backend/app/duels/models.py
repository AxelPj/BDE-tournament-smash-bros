from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_column
from app.users.models import User


class DuelStatus(StrEnum):
    PENDING = "pending"  # en attente de la réponse de l'adversaire
    ACCEPTED = "accepted"  # accepté, en attente de validation par un admin
    REFUSED = "refused"
    VALIDATED = "validated"  # validé par un admin, en attente de lancement
    IN_PROGRESS = "in_progress"  # lancé par un admin
    COMPLETED = "completed"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = (
    DuelStatus.PENDING,
    DuelStatus.ACCEPTED,
    DuelStatus.VALIDATED,
    DuelStatus.IN_PROGRESS,
)


class Duel(Base):
    """Match libre en 1 contre 1, hors tournoi. Ne rapporte rien en soi :
    les Tilt ne se gagnent que par les paris."""

    __tablename__ = "duels"
    __table_args__ = (CheckConstraint("challenger_id != opponent_id", name="distinct_players"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    challenger_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    opponent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[DuelStatus] = mapped_column(
        enum_column(DuelStatus), default=DuelStatus.PENDING
    )
    challenger_score: Mapped[int | None]
    opponent_score: Mapped[int | None]
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    validated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Incrémenté automatiquement à chaque modification : deux changements
    # simultanés du même duel ne peuvent pas s'écraser.
    version: Mapped[int] = mapped_column(default=0, server_default="0")

    __mapper_args__ = {"version_id_col": version}

    @property
    def betting_open(self) -> bool:
        return self.status is DuelStatus.VALIDATED

    challenger: Mapped[User] = relationship(foreign_keys=[challenger_id])
    opponent: Mapped[User] = relationship(foreign_keys=[opponent_id])
