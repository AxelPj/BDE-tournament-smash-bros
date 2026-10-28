"""Placement des joueurs (têtes de série) avant la génération du bracket."""

import random
from collections.abc import Sequence

from app.tournaments.bracket import BracketError


def seed_participants(
    participants: Sequence[int],
    seeded: Sequence[int] = (),
    rng: random.Random | None = None,
) -> list[int]:
    """Renvoie les participants triés par tête de série.

    Les joueurs de `seeded` sont placés en premier, dans l'ordre choisi par
    l'admin ; les autres sont tirés au sort à la suite. Donc :
    - `seeded` vide : placement entièrement aléatoire ;
    - `seeded` complet : placement entièrement manuel ;
    - entre les deux : têtes de série fixées, le reste aléatoire.
    """
    if len(set(seeded)) != len(seeded):
        raise BracketError("Une tête de série apparaît plusieurs fois")
    unknown = set(seeded) - set(participants)
    if unknown:
        raise BracketError(f"Têtes de série non inscrites : {sorted(unknown)}")

    rest = [p for p in participants if p not in set(seeded)]
    (rng or random.Random()).shuffle(rest)
    return [*seeded, *rest]
