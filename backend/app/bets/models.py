from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Bet(Base):
    """Une mise sur un duel OU sur un match de tournoi.

    Un match de tournoi est désigné par (tournoi, code) et non par sa ligne en
    base : celle-ci est recréée si le bracket est régénéré. Les deux joueurs
    sont mémorisés au moment du pari ; si une correction change l'affiche du
    match, le pari est remboursé.
    """

    __tablename__ = "bets"
    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint(
            "(duel_id IS NOT NULL AND tournament_id IS NULL AND match_code IS NULL)"
            " OR (duel_id IS NULL AND tournament_id IS NOT NULL AND match_code IS NOT NULL)",
            name="single_target",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    duel_id: Mapped[int | None] = mapped_column(ForeignKey("duels.id"), index=True)
    tournament_id: Mapped[int | None] = mapped_column(ForeignKey("tournaments.id"), index=True)
    match_code: Mapped[str | None] = mapped_column(String(8))
    picked_player_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    opponent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int]
    stake_transaction_id: Mapped[int] = mapped_column(ForeignKey("tilt_transactions.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def event_key(self) -> str:
        if self.duel_id is not None:
            return f"duel:{self.duel_id}"
        return f"match:{self.tournament_id}:{self.match_code}"
