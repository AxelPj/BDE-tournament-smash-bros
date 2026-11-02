from collections import defaultdict
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.gages.models import GageUseStatus
from app.shop.schemas import resolve_gage_image
from app.tournaments.bracket import MatchStatus, Side
from app.tournaments.models import Tournament, TournamentFormat, TournamentStatus
from app.tournaments.rewards import RewardSettings, reward_settings_of


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rewards: RewardSettings = Field(
        default_factory=RewardSettings,
        description="Montants en Tilt ; les valeurs omises prennent la valeur par défaut",
    )
    scheduled_date: date | None = None
    starts_at: str | None = None
    date_label: str | None = None
    max_players: int | None = Field(default=None, ge=2, le=256)
    has_losers_bracket: bool = True
    rules: list[dict[str, str]] | None = None

    @field_validator("scheduled_date")
    @classmethod
    def _reject_past_date(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("La date du tournoi ne peut pas être dans le passé")
        return v


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
    avatar_url: str | None = None
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
    starts_at: str | None = None
    date_label: str | None = None
    max_players: int | None = None
    has_losers_bracket: bool = True
    rules: list[dict[str, str]] | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, tournament: Tournament) -> "TournamentSummary":
        meta = (tournament.reward_settings or {}).get("_meta") or {}
        return cls(
            id=tournament.id,
            name=tournament.name,
            format=tournament.format,
            status=tournament.status,
            registration_open=tournament.registration_open,
            participant_count=len(tournament.participants),
            champion_id=tournament.champion_id,
            rewards=reward_settings_of(tournament),
            starts_at=meta.get("starts_at"),
            date_label=meta.get("date_label"),
            max_players=meta.get("max_players"),
            has_losers_bracket=meta.get("has_losers_bracket", True),
            rules=meta.get("rules"),
            created_at=tournament.created_at,
        )


SIDE_ORDER = {Side.WINNERS: 0, Side.LOSERS: 1, Side.GRAND_FINAL: 2}


class MatchGageRead(BaseModel):
    id: int
    imposer_id: int
    target_id: int
    status: GageUseStatus
    name: str
    description: str
    price: int = 0
    reward: int = 50
    image_url: str | None = None


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
    gages: list[MatchGageRead] = Field(default_factory=list)


def matches_from_tournament(tournament: Tournament) -> list[MatchRead]:
    default_reward = reward_settings_of(tournament).win_with_gage
    gages_by_code: dict[str, list[MatchGageRead]] = defaultdict(list)
    for u in getattr(tournament, "gage_uses", ()) or ():
        if u.status is GageUseStatus.CANCELLED or not u.match_code:
            continue
        g = u.gage
        gage_reward = (
            g.reward
            if getattr(g, "reward", None) is not None and g.reward > 0
            else default_reward
        )
        gages_by_code[u.match_code].append(
            MatchGageRead(
                id=u.id,
                imposer_id=u.imposer_id,
                target_id=u.target_id,
                status=u.status,
                name=g.name,
                description=g.description,
                price=g.price,
                reward=gage_reward,
                image_url=resolve_gage_image(g.name, g.image_url),
            )
        )
    sorted_matches = sorted(
        tournament.matches,
        key=lambda m: (SIDE_ORDER[m.side], m.round, m.position),
    )
    result: list[MatchRead] = []
    for m in sorted_matches:
        mr = MatchRead.model_validate(m)
        mr.gages = gages_by_code.get(m.code, [])
        result.append(mr)
    return result


class TournamentDetail(TournamentSummary):
    participants: list[ParticipantRead]
    matches: list[MatchRead] = Field(default_factory=list)

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
                    avatar_url=p.user.avatar_url,
                    seed=p.seed,
                    bracket_seed=p.bracket_seed,
                )
                for p in participants
            ],
            matches=matches_from_tournament(tournament),
        )


class ScoreResult(BaseModel):
    invalidated: list[str] = Field(
        description="Matchs dont le résultat a été annulé car la correction a changé leurs joueurs"
    )
    matches: list[MatchRead]
