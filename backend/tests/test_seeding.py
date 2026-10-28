import random

import pytest

from app.tournaments.bracket import BracketError
from app.tournaments.seeding import seed_participants

PLAYERS = [1, 2, 3, 4, 5, 6]


def test_manual_seeding_keeps_admin_order():
    assert seed_participants(PLAYERS, seeded=[4, 2, 6, 1, 3, 5]) == [4, 2, 6, 1, 3, 5]


def test_partial_seeding_puts_seeds_first_and_shuffles_the_rest():
    order = seed_participants(PLAYERS, seeded=[5, 3], rng=random.Random(0))

    assert order[:2] == [5, 3]
    assert sorted(order) == PLAYERS


def test_random_seeding_is_a_reproducible_permutation():
    first = seed_participants(PLAYERS, rng=random.Random(42))

    assert sorted(first) == PLAYERS
    assert first == seed_participants(PLAYERS, rng=random.Random(42))


def test_seeding_errors():
    with pytest.raises(BracketError):
        seed_participants(PLAYERS, seeded=[1, 1])
    with pytest.raises(BracketError):
        seed_participants(PLAYERS, seeded=[99])
