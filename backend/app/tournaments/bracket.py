"""Moteur de double élimination (Python pur, sans base de données).

Vocabulaire :
- WB : bracket gagnants, LB : bracket perdants.
- GF : grande finale (vainqueur du WB contre vainqueur du LB).
- GF-R : finale « reset », jouée seulement si le joueur venu du LB gagne la GF
  (il faut deux défaites pour être éliminé).
- Bye : place vide quand le nombre de joueurs n'est pas une puissance de 2.
  Un match contre un bye est validé automatiquement, sans être joué.

Identifiants des matchs : "W<tour>-<position>", "L<tour>-<position>", "GF", "GF-R".
"""

from dataclasses import dataclass, field
from enum import StrEnum

GRAND_FINAL_ID = "GF"
RESET_ID = "GF-R"


class BracketError(ValueError):
    pass


class Side(StrEnum):
    WINNERS = "winners"
    LOSERS = "losers"
    GRAND_FINAL = "grand_final"


class MatchStatus(StrEnum):
    PENDING = "pending"  # au moins un adversaire n'est pas encore connu
    READY = "ready"  # deux joueurs connus : le match peut être joué
    COMPLETED = "completed"
    SKIPPED = "skipped"  # finale reset inutile


@dataclass(frozen=True)
class SlotRef:
    """Une place (0 ou 1) dans un match."""

    match_id: str
    slot: int


@dataclass
class Match:
    id: str
    side: Side
    round: int
    position: int
    # Où vont le vainqueur et le perdant (None = sortie du bracket).
    winner_to: SlotRef | None = None
    loser_to: SlotRef | None = None
    players: list[int | None] = field(default_factory=lambda: [None, None])
    # Place décidée (joueur ou bye). Un joueur None sur une place décidée = bye.
    filled: list[bool] = field(default_factory=lambda: [False, False])
    status: MatchStatus = MatchStatus.PENDING
    winner: int | None = None
    loser: int | None = None

    @property
    def is_bye(self) -> bool:
        """Match validé automatiquement (au moins un bye) : à masquer à l'affichage."""
        return self.status is MatchStatus.COMPLETED and None in self.players


def standard_seed_order(size: int) -> list[int]:
    """Ordre des têtes de série dans le premier tour, pour que les meilleures
    ne se croisent que le plus tard possible. Ex. pour 8 : [1, 8, 4, 5, 2, 7, 3, 6]
    soit les matchs 1-8, 4-5, 2-7, 3-6. Les têtes de série les plus hautes
    affrontent les byes."""
    order = [1]
    while len(order) < size:
        total = len(order) * 2 + 1
        order = [seed for s in order for seed in (s, total - s)]
    return order


def _wb_id(round_: int, index: int) -> str:
    return f"W{round_}-{index + 1}"


def _lb_id(round_: int, index: int) -> str:
    return f"L{round_}-{index + 1}"


def _drop_position(wb_round: int, index: int, count: int) -> int:
    """Place dans le LB d'un perdant du WB (tour >= 2). L'ordre est alterné
    (inversé, puis décalé de moitié) pour éviter de recroiser trop tôt
    un adversaire déjà rencontré."""
    if wb_round % 2 == 0:
        return count - 1 - index
    return (index + count // 2) % count


def _build_matches(size: int) -> dict[str, Match]:
    """Construit la structure vide d'un bracket de `size` places (puissance de 2).

    Pour k = log2(size) : le WB a k tours, le LB en a 2(k-1).
    Tours impairs du LB : les survivants du LB s'affrontent entre eux
    (au tour 1 : les perdants du premier tour du WB).
    Tours pairs du LB : les survivants du LB affrontent les nouveaux perdants du WB.
    """
    k = size.bit_length() - 1
    lb_rounds = 2 * (k - 1)
    matches: dict[str, Match] = {}

    for r in range(1, k + 1):
        for i in range(size >> r):
            winner_to = (
                SlotRef(_wb_id(r + 1, i // 2), i % 2) if r < k else SlotRef(GRAND_FINAL_ID, 0)
            )
            if k == 1:
                loser_to = SlotRef(GRAND_FINAL_ID, 1)
            elif r == 1:
                loser_to = SlotRef(_lb_id(1, i // 2), i % 2)
            else:
                position = _drop_position(r, i, size >> r)
                loser_to = SlotRef(_lb_id(2 * (r - 1), position), 1)
            matches[_wb_id(r, i)] = Match(
                _wb_id(r, i), Side.WINNERS, r, i + 1, winner_to, loser_to
            )

    for r in range(1, lb_rounds + 1):
        for i in range(size >> ((r + 1) // 2 + 1)):
            if r == lb_rounds:
                winner_to = SlotRef(GRAND_FINAL_ID, 1)
            elif r % 2 == 1:
                winner_to = SlotRef(_lb_id(r + 1, i), 0)
            else:
                winner_to = SlotRef(_lb_id(r + 1, i // 2), i % 2)
            matches[_lb_id(r, i)] = Match(_lb_id(r, i), Side.LOSERS, r, i + 1, winner_to)

    matches[GRAND_FINAL_ID] = Match(GRAND_FINAL_ID, Side.GRAND_FINAL, 1, 1)
    matches[RESET_ID] = Match(RESET_ID, Side.GRAND_FINAL, 2, 1)
    return matches


class DoubleEliminationBracket:
    def __init__(self, participants: list[int]):
        """`participants` : identifiants des joueurs, triés par tête de série
        (le premier est la tête de série n°1). Voir seeding.seed_participants."""
        if len(participants) < 2:
            raise BracketError("Il faut au moins 2 participants")
        if len(set(participants)) != len(participants):
            raise BracketError("Un participant apparaît plusieurs fois")

        self.participants = list(participants)
        self.size = 2
        while self.size < len(participants):
            self.size *= 2
        self.matches = _build_matches(self.size)

        seeds = standard_seed_order(self.size)
        for index, seed in enumerate(seeds):
            player = participants[seed - 1] if seed <= len(participants) else None
            self._fill(SlotRef(_wb_id(1, index // 2), index % 2), player)

    def playable_matches(self) -> list[Match]:
        return [m for m in self.matches.values() if m.status is MatchStatus.READY]

    @property
    def champion(self) -> int | None:
        grand_final, reset = self.matches[GRAND_FINAL_ID], self.matches[RESET_ID]
        if reset.status is MatchStatus.COMPLETED:
            return reset.winner
        if reset.status is MatchStatus.SKIPPED:
            return grand_final.winner
        return None

    def report_result(self, match_id: str, winner: int) -> None:
        """Enregistre le vainqueur d'un match et fait avancer les deux joueurs."""
        match = self.matches.get(match_id)
        if match is None:
            raise BracketError(f"Match inconnu : {match_id}")
        if match.status is not MatchStatus.READY:
            raise BracketError(f"Le match {match_id} n'est pas jouable ({match.status})")
        if winner not in match.players:
            raise BracketError(f"Le joueur {winner} ne participe pas au match {match_id}")

        loser = match.players[1] if winner == match.players[0] else match.players[0]
        self._complete(match, winner, loser)

    def _fill(self, ref: SlotRef, player: int | None) -> None:
        match = self.matches[ref.match_id]
        match.players[ref.slot] = player
        match.filled[ref.slot] = True
        if not all(match.filled):
            return
        first, second = match.players
        if first is None or second is None:
            # Bye : le joueur présent (s'il y en a un) passe sans jouer.
            self._complete(match, winner=first if second is None else second, loser=None)
        else:
            match.status = MatchStatus.READY

    def _complete(self, match: Match, winner: int | None, loser: int | None) -> None:
        match.winner, match.loser = winner, loser
        match.status = MatchStatus.COMPLETED

        if match.id == GRAND_FINAL_ID:
            reset = self.matches[RESET_ID]
            if winner == match.players[0]:
                # Le vainqueur du WB gagne : son adversaire a sa 2e défaite.
                reset.status = MatchStatus.SKIPPED
            else:
                for slot, player in enumerate(match.players):
                    self._fill(SlotRef(RESET_ID, slot), player)
            return

        if match.winner_to:
            self._fill(match.winner_to, winner)
        if match.loser_to:
            self._fill(match.loser_to, loser)
