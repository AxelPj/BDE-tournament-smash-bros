"""Vue commune des duels et des matchs de tournoi, utilisée par les paris et les gages.

Un « match » est soit un duel, soit un match de tournoi désigné par (tournoi, code).
Ce module dit qui le joue actuellement, s'il est encore ouvert (pas lancé) et qui l'a gagné.
"""

from dataclasses import dataclass

from app.duels.models import Duel, DuelStatus
from app.tournaments.models import Tournament


@dataclass
class Outcome:
    players: tuple[int, int] | None  # affiche actuelle (None = match annulé ou inconnu)
    open: bool  # pas encore lancé : paris et gages acceptés
    started: bool  # lancé (ou terminé)
    winner: int | None  # connu une fois le match terminé
    label: str

    def has_players(self, a: int, b: int) -> bool:
        """Le match oppose toujours a et b (sinon une correction a changé l'affiche)."""
        return self.players is not None and {a, b} == set(self.players)


def duel_outcome(duel: Duel) -> Outcome:
    cancelled = duel.status in (DuelStatus.CANCELLED, DuelStatus.REFUSED)
    return Outcome(
        players=None if cancelled else (duel.challenger_id, duel.opponent_id),
        open=duel.status is DuelStatus.VALIDATED,
        started=duel.status in (DuelStatus.IN_PROGRESS, DuelStatus.COMPLETED),
        winner=duel.winner_id if duel.status is DuelStatus.COMPLETED else None,
        label=f"duel n°{duel.id}",
    )


def match_outcome(tournament: Tournament, code: str) -> Outcome:
    label = f"{code} — {tournament.name}"
    match = next((m for m in tournament.matches if m.code == code), None)
    if match is None or match.player1_id is None or match.player2_id is None:
        return Outcome(players=None, open=False, started=False, winner=None, label=label)
    played = match.result_order is not None
    return Outcome(
        players=(match.player1_id, match.player2_id),
        open=match.betting_open,
        started=match.started_at is not None or played,
        winner=match.winner_id if played else None,
        label=label,
    )
