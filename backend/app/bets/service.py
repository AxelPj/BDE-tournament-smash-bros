"""Paris mutuels sur les duels et les matchs de tournoi.

Cote d'un joueur = total misé sur le match / total misé sur ce joueur.
Si ce joueur gagne, chaque parieur reçoit sa mise × la cote (arrondi à l'unité
inférieure). Si personne n'a parié sur le vainqueur, tout le monde est remboursé.
Aucune commission.

Comme pour les récompenses de tournoi, les gains ne sont jamais calculés une
fois pour toutes : à chaque changement (résultat, correction, annulation), on
recalcule ce qui est dû et on verse ou reprend la différence.
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bets.models import Bet
from app.duels.models import Duel
from app.economy.models import TransactionKind
from app.economy.service import reconcile_credits, record_transaction
from app.matchups import Outcome, duel_outcome, match_outcome
from app.tournaments.models import Tournament
from app.users.models import User


class BettingClosedError(Exception):
    pass


class ForbiddenBetError(Exception):
    pass


def _is_valid(bet: Bet, outcome: Outcome) -> bool:
    """Le pari porte sur l'affiche actuelle du match."""
    return outcome.has_players(bet.picked_player_id, bet.opponent_id)


# --- Prise de pari ---


def _place(
    db: Session, user: User, outcome: Outcome, picked_player_id: int, amount: int, **target
) -> Bet:
    if not outcome.open:
        raise BettingClosedError("Les paris sont fermés pour ce match")
    if picked_player_id not in outcome.players:
        raise ValueError("Ce joueur ne participe pas à ce match")
    if user.id in outcome.players and picked_player_id != user.id:
        raise ForbiddenBetError("Dans ton propre match, tu ne peux parier que sur toi")
    other_side = db.scalar(
        select(Bet.id).filter_by(user_id=user.id, **target).where(Bet.picked_player_id != picked_player_id)
    )
    if other_side:
        raise ForbiddenBetError("Tu as déjà parié sur l'autre joueur de ce match")

    opponent_id = next(p for p in outcome.players if p != picked_player_id)
    # Lève InsufficientFundsError si le solde ne suffit pas.
    stake = record_transaction(
        db, user.id, -amount, TransactionKind.BET_STAKE, f"Mise — {outcome.label}"
    )
    bet = Bet(
        user_id=user.id,
        picked_player_id=picked_player_id,
        opponent_id=opponent_id,
        amount=amount,
        stake_transaction_id=stake.id,
        **target,
    )
    db.add(bet)
    db.commit()
    return bet


def place_duel_bet(db: Session, user: User, duel: Duel, picked_player_id: int, amount: int) -> Bet:
    return _place(db, user, duel_outcome(duel), picked_player_id, amount, duel_id=duel.id)


def place_match_bet(
    db: Session, user: User, tournament: Tournament, code: str, picked_player_id: int, amount: int
) -> Bet:
    return _place(
        db,
        user,
        match_outcome(tournament, code),
        picked_player_id,
        amount,
        tournament_id=tournament.id,
        match_code=code,
    )


# --- Cotes ---


def market(bets: list[Bet], outcome: Outcome) -> tuple[int, dict[int, int]]:
    """(total misé, total misé par joueur) en ne comptant que les paris valides."""
    staked = {player: 0 for player in outcome.players or ()}
    for bet in bets:
        if _is_valid(bet, outcome):
            staked[bet.picked_player_id] += bet.amount
    return sum(staked.values()), staked


def duel_bets(db: Session, duel: Duel) -> list[Bet]:
    return list(db.scalars(select(Bet).where(Bet.duel_id == duel.id)))


def match_bets(db: Session, tournament: Tournament, code: str) -> list[Bet]:
    return list(
        db.scalars(select(Bet).where(Bet.tournament_id == tournament.id, Bet.match_code == code))
    )


# --- Règlement ---


def _payouts(bets: list[Bet], outcome: Outcome) -> dict[int, int]:
    """Montant dû à chaque parieur d'après l'état actuel du match."""
    due: dict[int, int] = defaultdict(int)
    valid = [b for b in bets if _is_valid(b, outcome)]
    for bet in bets:
        if not _is_valid(bet, outcome):
            due[bet.user_id] += bet.amount  # affiche changée ou match annulé : remboursé

    if outcome.winner is None or not valid:
        return due
    total = sum(b.amount for b in valid)
    winning = [b for b in valid if b.picked_player_id == outcome.winner]
    winning_pool = sum(b.amount for b in winning)
    if winning_pool == 0:
        for bet in valid:  # personne sur le vainqueur : tout le monde est remboursé
            due[bet.user_id] += bet.amount
        return due

    stake_on_winner: dict[int, int] = defaultdict(int)
    for bet in winning:
        stake_on_winner[bet.user_id] += bet.amount
    for user_id, stake in stake_on_winner.items():
        due[user_id] += stake * total // winning_pool
    return due


def _settle(db: Session, event_key: str, bets: list[Bet], outcome: Outcome) -> None:
    prefix = f"bet:{event_key}:"
    desired = {
        f"{prefix}user:{user_id}": (user_id, amount, f"Gain de pari — {outcome.label}")
        for user_id, amount in _payouts(bets, outcome).items()
        if amount > 0
    }
    reconcile_credits(
        db,
        prefix=prefix,
        desired=desired,
        kind=TransactionKind.BET_PAYOUT,
        cancelled_label=f"Gain de pari annulé — {outcome.label}",
    )


def settle_duel(db: Session, duel: Duel) -> None:
    """À appeler après chaque changement d'état d'un duel. Ne commit pas."""
    _settle(db, f"duel:{duel.id}", duel_bets(db, duel), duel_outcome(duel))


def settle_tournament(db: Session, tournament: Tournament) -> None:
    """À appeler après chaque changement du bracket. Ne commit pas."""
    codes = db.scalars(
        select(Bet.match_code).where(Bet.tournament_id == tournament.id).distinct()
    ).all()
    for code in codes:
        _settle(
            db,
            f"match:{tournament.id}:{code}",
            match_bets(db, tournament, code),
            match_outcome(tournament, code),
        )


# --- Historique du joueur ---


def bet_status(bet: Bet, bets_of_event: list[Bet], outcome: Outcome) -> tuple[str, int | None]:
    """(statut, gain) d'un pari : open, closed, won, lost ou refunded."""
    if not _is_valid(bet, outcome):
        return "refunded", bet.amount
    if outcome.winner is None:
        return ("open" if outcome.open else "closed"), None
    total, staked = market(bets_of_event, outcome)
    winning_pool = staked[outcome.winner]
    if winning_pool == 0:
        return "refunded", bet.amount
    if bet.picked_player_id == outcome.winner:
        return "won", bet.amount * total // winning_pool
    return "lost", 0


def my_bets(db: Session, user: User) -> list[tuple[Bet, str, int | None]]:
    bets = list(db.scalars(select(Bet).where(Bet.user_id == user.id).order_by(Bet.id.desc())))
    outcomes: dict[str, tuple[Outcome, list[Bet]]] = {}
    result = []
    for bet in bets:
        if bet.event_key not in outcomes:
            if bet.duel_id is not None:
                duel = db.get(Duel, bet.duel_id)
                outcomes[bet.event_key] = (duel_outcome(duel), duel_bets(db, duel))
            else:
                tournament = db.get(Tournament, bet.tournament_id)
                outcomes[bet.event_key] = (
                    match_outcome(tournament, bet.match_code),
                    match_bets(db, tournament, bet.match_code),
                )
        outcome, event_bets = outcomes[bet.event_key]
        result.append((bet, *bet_status(bet, event_bets, outcome)))
    return result
