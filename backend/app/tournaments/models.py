from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_column
from app.tournaments.bracket import MatchStatus, Side
from app.users.models import User


class TournamentStatus(StrEnum):
    REGISTRATION = "registration"  # inscriptions, bracket pas encore généré
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TournamentFormat(StrEnum):
    DOUBLE_ELIMINATION = "double_elimination"


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    format: Mapped[TournamentFormat] = mapped_column(
        enum_column(TournamentFormat), default=TournamentFormat.DOUBLE_ELIMINATION
    )
    status: Mapped[TournamentStatus] = mapped_column(
        enum_column(TournamentStatus), default=TournamentStatus.REGISTRATION
    )
    # Inscription libre des joueurs. Les admins peuvent toujours ajouter/retirer
    # des participants tant que le bracket n'est pas généré.
    registration_open: Mapped[bool] = mapped_column(default=True, server_default="1")
    champion_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # Montants des récompenses en Tilt (voir rewards.RewardSettings).
    # Toujours réassigner un nouveau dict : une modification en place ne serait pas enregistrée.
    reward_settings: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    # Incrémenté à chaque modification du bracket. Si deux admins modifient
    # en même temps, la seconde écriture échoue au lieu d'écraser la première.
    version: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    matches: Mapped[list["TournamentMatch"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id"),
        UniqueConstraint("tournament_id", "seed"),
        UniqueConstraint("tournament_id", "bracket_seed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Tête de série choisie par l'admin (optionnelle).
    seed: Mapped[int | None]
    # Rang définitif (1 à n) attribué à la génération du bracket.
    bracket_seed: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tournament: Mapped[Tournament] = relationship(back_populates="participants")
    user: Mapped[User] = relationship()


class TournamentMatch(Base):
    """Copie en base de l'état d'un match du moteur (app/tournaments/bracket.py).
    Les joueurs sont des identifiants d'utilisateurs."""

    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("tournament_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(8))  # ex. "W1-1", "L3-2", "GF"
    side: Mapped[Side] = mapped_column(enum_column(Side))
    round: Mapped[int]
    position: Mapped[int]
    player1_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    player2_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[MatchStatus] = mapped_column(enum_column(MatchStatus))
    score1: Mapped[int | None]
    score2: Mapped[int | None]
    # Ordre de saisie des résultats (None = pas de résultat saisi).
    # Sert à rejouer le bracket après une correction.
    result_order: Mapped[int | None]
    # Lancé par un admin : ferme les paris.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tournament: Mapped[Tournament] = relationship(back_populates="matches")

    @property
    def betting_open(self) -> bool:
        return self.status is MatchStatus.READY and self.started_at is None

    @property
    def is_bye(self) -> bool:
        return self.status is MatchStatus.COMPLETED and (
            self.player1_id is None or self.player2_id is None
        )
