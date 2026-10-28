"""Gages imposés dans un match.

    owned ─(un joueur du match l'impose, avant le lancement)→ engaged
    engaged ─(retiré par son auteur avant le lancement, ou match annulé)→ owned
    engaged ─(un admin valide : réalisé ou non)→ consumed

Récompense « gagner avec un gage » : pour chaque gage validé comme réalisé,
si sa cible gagne le match. Montant réglable par tournoi (RewardSettings) et,
pour les duels, dans les réglages globaux. Recalculée à chaque changement,
comme les autres récompenses.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.duels.models import Duel
from app.economy.models import TransactionKind
from app.economy.service import reconcile_credits
from app.gages.models import GageUse, GageUseStatus
from app.gages.rules import winning_gage_uses
from app.game_settings.service import get_game_settings
from app.matchups import Outcome, duel_outcome, match_outcome
from app.shop.models import InventoryItem, InventoryStatus
from app.tournaments.models import Tournament
from app.tournaments.rewards import reconcile_rewards
from app.users.models import User


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class GageStateError(Exception):
    pass


# --- Imposer / retirer ---


def _impose(
    db: Session, user: User, outcome: Outcome, item_id: int, target_id: int, **target
) -> GageUse:
    if outcome.players is None or user.id not in outcome.players:
        raise ForbiddenError("Seuls les joueurs du match peuvent imposer un gage")
    if not outcome.open:
        raise GageStateError("Les gages s'imposent avant le lancement du match")
    if target_id not in outcome.players:
        raise ValueError("La cible doit être un joueur du match")
    item = db.get(InventoryItem, item_id)
    if item is None or item.user_id != user.id:
        raise NotFoundError("Gage introuvable dans ton inventaire")
    if item.status is not InventoryStatus.OWNED:
        raise GageStateError("Ce gage est déjà engagé ou utilisé")

    already = [
        use
        for use in db.scalars(select(GageUse).filter_by(imposer_id=user.id, **target))
        if use.status is GageUseStatus.ENGAGED
    ]
    limit = get_game_settings(db).max_gages_per_player
    if len(already) >= limit:
        raise GageStateError(f"Limite atteinte : {limit} gage(s) par joueur et par match")

    item.status = InventoryStatus.ENGAGED
    use = GageUse(
        item=item,
        imposer_id=user.id,
        target_id=target_id,
        other_player_id=next(p for p in outcome.players if p != user.id),
        **target,
    )
    db.add(use)
    db.commit()
    return use


def impose_on_duel(db: Session, user: User, duel: Duel, item_id: int, target_id: int) -> GageUse:
    return _impose(db, user, duel_outcome(duel), item_id, target_id, duel_id=duel.id)


def impose_on_match(
    db: Session, user: User, tournament: Tournament, code: str, item_id: int, target_id: int
) -> GageUse:
    return _impose(
        db,
        user,
        match_outcome(tournament, code),
        item_id,
        target_id,
        tournament_id=tournament.id,
        match_code=code,
    )


def get_use(db: Session, use_id: int) -> GageUse:
    use = db.get(GageUse, use_id)
    if use is None:
        raise NotFoundError("Gage imposé introuvable")
    return use


def outcome_of(db: Session, use: GageUse) -> Outcome:
    if use.duel_id is not None:
        return duel_outcome(db.get(Duel, use.duel_id))
    return match_outcome(db.get(Tournament, use.tournament_id), use.match_code)


def _release(use: GageUse) -> None:
    use.status = GageUseStatus.CANCELLED
    use.item.status = InventoryStatus.OWNED


def withdraw(db: Session, use: GageUse, user: User) -> GageUse:
    """Son auteur retire un gage imposé, tant que le match n'est pas lancé."""
    if use.imposer_id != user.id:
        raise ForbiddenError("Seul le joueur qui a imposé ce gage peut le retirer")
    if use.status is not GageUseStatus.ENGAGED or not outcome_of(db, use).open:
        raise GageStateError("Ce gage ne peut plus être retiré")
    _release(use)
    db.commit()
    return use


# --- Validation par un admin ---


def validate(db: Session, use: GageUse, admin: User, completed: bool) -> GageUse:
    """L'admin indique si le gage a été réalisé. Le gage est alors consommé.
    Une décision déjà prise peut être corrigée."""
    if use.status is GageUseStatus.CANCELLED:
        raise GageStateError("Ce gage a été retiré ou annulé")
    outcome = outcome_of(db, use)
    if not outcome.started:
        raise GageStateError("Le match n'a pas encore été lancé")
    use.status = GageUseStatus.COMPLETED if completed else GageUseStatus.FAILED
    use.validated_by_id = admin.id
    use.validated_at = datetime.now(UTC)
    use.item.status = InventoryStatus.CONSUMED
    use.item.used_at = use.item.used_at or use.validated_at
    if use.duel_id is not None:
        reconcile_duel_rewards(db, db.get(Duel, use.duel_id))
    else:
        reconcile_rewards(db, db.get(Tournament, use.tournament_id))
    db.commit()
    return use


def list_uses(db: Session, **filters) -> list[GageUse]:
    return list(db.scalars(select(GageUse).filter_by(**filters).order_by(GageUse.id)))


# --- Synchronisation après un changement du match (appelées sans commit) ---


def _release_invalid(uses: list[GageUse], outcome: Outcome) -> None:
    """Rend à leur propriétaire les gages engagés dans un match annulé ou dont
    l'affiche a changé (correction de bracket)."""
    for use in uses:
        if use.status is GageUseStatus.ENGAGED and not outcome.has_players(
            use.imposer_id, use.other_player_id
        ):
            _release(use)


def sync_duel(db: Session, duel: Duel) -> None:
    _release_invalid(list_uses(db, duel_id=duel.id), duel_outcome(duel))
    reconcile_duel_rewards(db, duel)


def sync_tournament(db: Session, tournament: Tournament) -> None:
    uses = list_uses(db, tournament_id=tournament.id)
    for code in {use.match_code for use in uses}:
        _release_invalid(
            [u for u in uses if u.match_code == code], match_outcome(tournament, code)
        )


def reconcile_duel_rewards(db: Session, duel: Duel) -> None:
    amount = get_game_settings(db).duel_gage_win_reward
    outcome = duel_outcome(duel)
    prefix = f"duel:{duel.id}:gage:"
    desired = {
        f"{prefix}{use.id}:user:{use.target_id}": (
            use.target_id,
            amount,
            f"Victoire avec un gage — {outcome.label}",
        )
        for use in winning_gage_uses(list_uses(db, duel_id=duel.id), outcome)
        if amount
    }
    reconcile_credits(
        db,
        prefix=prefix,
        desired=desired,
        kind=TransactionKind.GAGE_REWARD,
        cancelled_label=f"Récompense de gage annulée — {outcome.label}",
    )
