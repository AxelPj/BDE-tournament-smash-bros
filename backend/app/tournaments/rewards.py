"""Récompenses en Tilt des tournois.

Principe : après chaque changement (génération, score, correction, annulation,
modification des montants), on calcule ce que chaque joueur DEVRAIT avoir reçu
d'après l'état actuel du tournoi, on compare avec ce qui a déjà été versé, et
on verse ou reprend la différence. Les corrections de score sont ainsi
répercutées automatiquement, et rien ne peut être payé deux fois.
"""

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy.models import TransactionKind
from app.economy.service import reconcile_credits
from app.gages.models import GageUse
from app.gages.rules import winning_gage_uses
from app.matchups import match_outcome
from app.tournaments.bracket import GRAND_FINAL_ID, RESET_ID, MatchStatus, Side
from app.tournaments.models import Tournament, TournamentMatch, TournamentStatus


class RewardSettings(BaseModel):
    """Montants en Tilt, réglables par tournoi."""

    participation: int = Field(default=100, ge=0, le=100_000)
    match_played: int = Field(default=10, ge=0, le=100_000)
    match_won: int = Field(default=20, ge=0, le=100_000)
    top8: int = Field(default=30, ge=0, le=100_000, description="5e à 8e")
    top4: int = Field(default=60, ge=0, le=100_000, description="3e et 4e")
    finalist: int = Field(default=100, ge=0, le=100_000)
    champion: int = Field(default=200, ge=0, le=100_000)
    win_with_gage: int = Field(
        default=50, ge=0, le=100_000, description="Par gage réalisé dont la cible gagne le match"
    )


PLACEMENT_LABELS = {
    "champion": "Champion",
    "finalist": "Finaliste",
    "top4": "Top 4",
    "top8": "Top 8",
}


def reward_settings_of(tournament: Tournament) -> RewardSettings:
    # Les montants absents de la base prennent la valeur par défaut.
    return RewardSettings(**(tournament.reward_settings or {}))


def _loser(match: TournamentMatch) -> int | None:
    if match.result_order is None:  # non joué, ou bye
        return None
    return match.player2_id if match.winner_id == match.player1_id else match.player1_id


def placement_tiers(tournament: Tournament) -> dict[int, str]:
    """Palier de classement de chaque joueur concerné, une fois le tournoi terminé.

    Le classement d'une double élimination dépend du tour du bracket perdants
    où le joueur est éliminé : dernier tour = 3e, avant-dernier = 4e,
    les deux tours précédents = 5e à 8e.
    """
    if tournament.status is not TournamentStatus.COMPLETED:
        return {}
    by_code = {m.code: m for m in tournament.matches}
    reset = by_code[RESET_ID]
    final = reset if reset.status is MatchStatus.COMPLETED else by_code[GRAND_FINAL_ID]

    tiers = {tournament.champion_id: "champion", _loser(final): "finalist"}
    lb_rounds = max((m.round for m in tournament.matches if m.side is Side.LOSERS), default=0)
    for match in tournament.matches:
        loser = _loser(match)
        if match.side is Side.LOSERS and loser is not None:
            depth = lb_rounds - match.round
            if depth <= 1:
                tiers[loser] = "top4"
            elif depth <= 3:
                tiers[loser] = "top8"
    return tiers


def desired_rewards(db: Session, tournament: Tournament) -> dict[str, tuple[int, int, str]]:
    """Récompenses dues d'après l'état actuel : {clé: (joueur, montant, libellé)}."""
    settings = reward_settings_of(tournament)
    rewards: dict[str, tuple[int, int, str]] = {}

    def add(key: str, user_id: int, amount: int, label: str) -> None:
        if amount:
            rewards[f"tournament:{tournament.id}:{key}:user:{user_id}"] = (
                user_id,
                amount,
                f"{label} — {tournament.name}",
            )

    if tournament.status is TournamentStatus.REGISTRATION:
        return rewards
    for participant in tournament.participants:
        add("participation", participant.user_id, settings.participation, "Participation")
    for match in tournament.matches:
        if match.result_order is None:
            continue
        for user_id in (match.player1_id, match.player2_id):
            add(f"played:{match.code}", user_id, settings.match_played, f"Match joué ({match.code})")
        add(f"won:{match.code}", match.winner_id, settings.match_won, f"Match gagné ({match.code})")
    for user_id, tier in placement_tiers(tournament).items():
        add("placement", user_id, getattr(settings, tier), PLACEMENT_LABELS[tier])

    uses = list(db.scalars(select(GageUse).where(GageUse.tournament_id == tournament.id)))
    for code in sorted({use.match_code for use in uses}):
        outcome = match_outcome(tournament, code)
        for use in winning_gage_uses([u for u in uses if u.match_code == code], outcome):
            add(f"gage:{use.id}", use.target_id, settings.win_with_gage, f"Victoire avec un gage ({code})")
    return rewards


def reconcile_rewards(db: Session, tournament: Tournament) -> None:
    """Verse ou reprend la différence entre le dû et le déjà versé. Ne commit pas."""
    reconcile_credits(
        db,
        prefix=f"tournament:{tournament.id}:",
        desired=desired_rewards(db, tournament),
        kind=TransactionKind.TOURNAMENT_REWARD,
        cancelled_label=f"Récompense annulée — {tournament.name}",
    )
