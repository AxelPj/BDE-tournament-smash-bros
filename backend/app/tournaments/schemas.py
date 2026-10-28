from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.tournaments.bracket import MatchStatus, Side
from app.tournaments.models import Tournament, TournamentFormat, TournamentStatus
from app.tournaments.rewards import RewardSettings, reward_settings_of


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rewards: RewardSettings = Field(
        default_factory=RewardSettings,
        description="Montants en Tilt ; les valeurs omises prennent la valeur par défaut",
    )


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    registration_open: bool | None = None
    rewards: RewardSettings | None = Field(
        default=None,
        description="Remplace tous les montants. Les récompenses déjà versées sont ajustées.",
    )


class ParticipantAdd(BaseModel):
    user_id: int


class SeedsUpdate(BaseModel):
    user_ids: list[int] = Field(description="Ordre des têtes de série : le premier est n°1")


class ScoreReport(BaseModel):
    """Score du joueur 1 et du joueur 2 du match (pas de match nul)."""

    score1: int = Field(ge=0, le=99)
    score2: int = Field(ge=0, le=99)


class ParticipantRead(BaseModel):
    user_id: int
    username: str
    display_name: str
    seed: int | None = Field(description="Tête de série choisie par l'admin")
    bracket_seed: int | None = Field(description="Rang définitif après génération")


class TournamentSummary(BaseModel):
    id: int
    name: str
    format: TournamentFormat
    status: TournamentStatus
    registration_open: bool
    participant_count: int
    champion_id: int | None
    rewards: RewardSettings
    created_at: datetime

    @classmethod
    def from_model(cls, tournament: Tournament) -> "TournamentSummary":
        return cls(
            id=tournament.id,
            name=tournament.name,
            format=tournament.format,
            status=tournament.status,
            registration_open=tournament.registration_open,
            participant_count=len(tournament.participants),
            champion_id=tournament.champion_id,
            rewards=reward_settings_of(tournament),
            created_at=tournament.created_at,
        )


class TournamentDetail(TournamentSummary):
    participants: list[ParticipantRead]

    @classmethod
    def from_model(cls, tournament: Tournament) -> "TournamentDetail":
        participants = sorted(
            tournament.participants,
            key=lambda p: (
                p.bracket_seed or 0,
                p.seed is None,
                p.seed or 0,
                p.user.display_name.lower(),
            ),
        )
        return cls(
            **TournamentSummary.from_model(tournament).model_dump(),
            participants=[
                ParticipantRead(
                    user_id=p.user_id,
                    username=p.user.username,
                    display_name=p.user.display_name,
                    seed=p.seed,
                    bracket_seed=p.bracket_seed,
                )
                for p in participants
            ],
        )


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    side: Side
    round: int
    position: int
    player1_id: int | None
    player2_id: int | None
    winner_id: int | None
    score1: int | None
    score2: int | None
    status: MatchStatus
    started_at: datetime | None
    betting_open: bool = Field(description="Paris acceptés (match jouable et pas encore lancé)")
    is_bye: bool = Field(description="Validé automatiquement (adversaire absent) : à masquer")


class ScoreResult(BaseModel):
    invalidated: list[str] = Field(
        description="Matchs dont le résultat a été annulé car la correction a changé leurs joueurs"
    )
    matches: list[MatchRead]
