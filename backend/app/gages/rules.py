"""Règle partagée par les récompenses de tournoi et de duel (sans dépendance
vers les services, pour éviter les imports circulaires)."""

from app.gages.models import GageUse, GageUseStatus
from app.matchups import Outcome


def winning_gage_uses(uses: list[GageUse], outcome: Outcome) -> list[GageUse]:
    """Gages réalisés dont la cible a gagné le match (affiche inchangée).
    Chacun rapporte la récompense « gagner avec un gage »."""
    return [
        use
        for use in uses
        if use.status is GageUseStatus.COMPLETED
        and outcome.has_players(use.imposer_id, use.other_player_id)
        and outcome.winner == use.target_id
    ]
