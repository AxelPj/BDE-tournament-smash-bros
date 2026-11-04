"""Paris mutuels sur les duels et les matchs de tournoi.

Cote d'un joueur = nombre de parieurs du match / nombre de parieurs sur ce
joueur (chaque parieur compte une fois, quel que soit le montant misé), avec un
plancher : la cote minimale garantie (réglage global `bet_min_odds`).
Si ce joueur gagne, chaque parieur reçoit sa mise × la cote (arrondi à l'unité
inférieure). La banque complète ou garde la différence avec les mises perdues :
des Tilt peuvent être créés ou détruits. Si personne n'a parié sur le vainqueur,
tout le monde est remboursé. Aucune commission.

Comme pour les récompenses de tournoi, les gains ne sont jamais calculés une
fois pour toutes : à chaque changement (résultat, correction, annulation), on
recalcule ce qui est dû et on verse ou reprend la différence.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bets.models import Bet
from app.duels.models import Duel
from app.economy.models import TransactionKind
from app.economy.service import reconcile_credits, record_transaction
from app.game_settings.service import get_game_settings
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


def min_odds_cents(db: Session) -> int:
    """Cote minimale garantie, en centièmes (1.2 -> 120) pour calculer en entiers."""
    return round(get_game_settings(db).bet_min_odds * 100)


def odds(total_bettors: int, bettors: int, min_cents: int) -> float | None:
    """Cote affichée d'un joueur (None tant que personne n'a parié sur lui)."""
    if not bettors:
        return None
    return max(round(total_bettors / bettors, 2), min_cents / 100)


def _gain(stake: int, total_bettors: int, winner_bettors: int, min_cents: int) -> int:
    """Gain d'une mise gagnante : mise × cote, jamais moins que la cote minimale."""
    return max(stake * total_bettors // winner_bettors, stake * min_cents // 100)


@dataclass
class Market:
    """État des paris valides d'un match."""

    staked: dict[int, int]  # Tilt misés par joueur
    bettors: dict[int, set[int]] = field(default_factory=dict)  # parieurs par joueur

    @property
    def total(self) -> int:
        return sum(self.staked.values())

    @property
    def total_bettors(self) -> int:
        return sum(len(users) for users in self.bettors.values())

    def bettor_count(self, player_id: int) -> int:
        return len(self.bettors.get(player_id, ()))


def market(bets: list[Bet], outcome: Outcome) -> Market:
    """Mises et parieurs par joueur, en ne comptant que les paris valides.
    Un parieur ne peut miser que d'un côté : il n'est compté qu'une fois."""
    players = outcome.players or ()
    result = Market(staked={p: 0 for p in players}, bettors={p: set() for p in players})
    for bet in bets:
        if _is_valid(bet, outcome):
            result.staked[bet.picked_player_id] += bet.amount
            result.bettors[bet.picked_player_id].add(bet.user_id)
    return result


def duel_bets(db: Session, duel: Duel) -> list[Bet]:
    return list(db.scalars(select(Bet).where(Bet.duel_id == duel.id)))


def match_bets(db: Session, tournament: Tournament, code: str) -> list[Bet]:
    return list(
        db.scalars(select(Bet).where(Bet.tournament_id == tournament.id, Bet.match_code == code))
    )


# --- Règlement ---


def _payouts(bets: list[Bet], outcome: Outcome, min_cents: int) -> dict[int, int]:
    """Montant dû à chaque parieur d'après l'état actuel du match."""
    due: dict[int, int] = defaultdict(int)
    valid = [b for b in bets if _is_valid(b, outcome)]
    for bet in bets:
        if not _is_valid(bet, outcome):
            due[bet.user_id] += bet.amount  # affiche changée ou match annulé : remboursé

    if outcome.winner is None or not valid:
        return due
    state = market(valid, outcome)
    winner_bettors = state.bettor_count(outcome.winner)
    winning = [b for b in valid if b.picked_player_id == outcome.winner]
    if winner_bettors == 0:
        for bet in valid:  # personne sur le vainqueur : tout le monde est remboursé
            due[bet.user_id] += bet.amount
        return due

    stake_on_winner: dict[int, int] = defaultdict(int)
    for bet in winning:
        stake_on_winner[bet.user_id] += bet.amount
    for user_id, stake in stake_on_winner.items():
        due[user_id] += _gain(stake, state.total_bettors, winner_bettors, min_cents)
    return due


def _settle(db: Session, event_key: str, bets: list[Bet], outcome: Outcome) -> None:
    prefix = f"bet:{event_key}:"
    desired = {
        f"{prefix}user:{user_id}": (user_id, amount, f"Gain de pari — {outcome.label}")
        for user_id, amount in _payouts(bets, outcome, min_odds_cents(db)).items()
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


def bet_status(
    bet: Bet, bets_of_event: list[Bet], outcome: Outcome, min_cents: int
) -> tuple[str, int | None]:
    """(statut, gain) d'un pari : open, closed, won, lost ou refunded."""
    if not _is_valid(bet, outcome):
        return "refunded", bet.amount
    if outcome.winner is None:
        return ("open" if outcome.open else "closed"), None
    state = market(bets_of_event, outcome)
    winner_bettors = state.bettor_count(outcome.winner)
    if winner_bettors == 0:
        return "refunded", bet.amount
    if bet.picked_player_id == outcome.winner:
        return "won", _gain(bet.amount, state.total_bettors, winner_bettors, min_cents)
    return "lost", 0


def my_bets(db: Session, user: User) -> list[tuple[Bet, str, int | None]]:
    bets = list(db.scalars(select(Bet).where(Bet.user_id == user.id).order_by(Bet.id.desc())))
    outcomes: dict[str, tuple[Outcome, list[Bet]]] = {}
    min_cents = min_odds_cents(db)
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
        result.append((bet, *bet_status(bet, event_bets, outcome, min_cents)))
    return result
