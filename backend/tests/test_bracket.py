import random
from collections import Counter

import pytest

from app.tournaments.bracket import (
    GRAND_FINAL_ID,
    RESET_ID,
    BracketError,
    DoubleEliminationBracket,
    MatchStatus,
    Side,
    standard_seed_order,
)


def play_out(bracket, rng):
    """Joue tous les matchs jusqu'à la fin, vainqueurs tirés au sort."""
    played = []
    while ready := bracket.playable_matches():
        match = rng.choice(ready)
        played.append(match)
        bracket.report_result(match.id, rng.choice(match.players))
    return played


def test_standard_seed_order():
    assert standard_seed_order(2) == [1, 2]
    assert standard_seed_order(4) == [1, 4, 2, 3]
    assert standard_seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]


@pytest.mark.parametrize("n", range(2, 34))
def test_structure(n):
    bracket = DoubleEliminationBracket(list(range(1, n + 1)))
    sides = Counter(m.side for m in bracket.matches.values())

    assert sides[Side.WINNERS] == bracket.size - 1
    assert sides[Side.LOSERS] == bracket.size - 2
    assert sides[Side.GRAND_FINAL] == 2

    # Chaque place hors premier tour du WB et finale reset est alimentée
    # par exactement un match précédent.
    incoming = Counter()
    for match in bracket.matches.values():
        for ref in (match.winner_to, match.loser_to):
            if ref:
                assert ref.match_id in bracket.matches
                incoming[ref] += 1
    assert all(count == 1 for count in incoming.values())
    expected = sum(
        2 for m in bracket.matches.values()
        if not (m.side is Side.WINNERS and m.round == 1) and m.id != RESET_ID
    )
    assert len(incoming) == expected


@pytest.mark.parametrize("n", range(2, 34))
@pytest.mark.parametrize("seed", range(5))
def test_full_tournament_invariants(n, seed):
    players = list(range(1, n + 1))
    bracket = DoubleEliminationBracket(players)

    played = play_out(bracket, random.Random(seed))

    champion = bracket.champion
    losses = Counter(m.loser for m in played)
    assert champion in players
    # Double élimination : tout le monde sauf le champion a exactement 2 défaites.
    assert all(losses[p] == 2 for p in players if p != champion)
    assert losses[champion] <= 1
    # 2n-2 matchs joués, +1 si la finale reset a eu lieu.
    assert len(played) in (2 * n - 2, 2 * n - 1)
    # Aucun match réellement joué contre un bye, et plus rien en attente.
    assert all(None not in m.players for m in played)
    assert all(
        m.status in (MatchStatus.COMPLETED, MatchStatus.SKIPPED)
        for m in bracket.matches.values()
    )


def test_top_seeds_get_byes():
    bracket = DoubleEliminationBracket([10, 20, 30])

    bye_match = bracket.matches["W1-1"]
    assert bye_match.players == [10, None]
    assert bye_match.is_bye
    assert bracket.matches["W2-1"].players[0] == 10
    assert [m.id for m in bracket.playable_matches()] == ["W1-2"]


def test_six_players_seeds_one_and_two_have_byes():
    bracket = DoubleEliminationBracket([1, 2, 3, 4, 5, 6])

    byes = {m.winner for m in bracket.matches.values() if m.side is Side.WINNERS and m.is_bye}
    assert byes == {1, 2}


def test_grand_final_won_by_winners_side_skips_reset():
    bracket = DoubleEliminationBracket([1, 2])
    bracket.report_result("W1-1", 1)

    assert bracket.matches[GRAND_FINAL_ID].players == [1, 2]
    bracket.report_result(GRAND_FINAL_ID, 1)

    assert bracket.matches[RESET_ID].status is MatchStatus.SKIPPED
    assert bracket.champion == 1


def test_grand_final_won_by_losers_side_triggers_reset():
    bracket = DoubleEliminationBracket([1, 2])
    bracket.report_result("W1-1", 1)
    bracket.report_result(GRAND_FINAL_ID, 2)

    reset = bracket.matches[RESET_ID]
    assert reset.status is MatchStatus.READY
    assert reset.players == [1, 2]
    assert bracket.champion is None

    bracket.report_result(RESET_ID, 2)
    assert bracket.champion == 2


def test_winner_and_loser_advance():
    bracket = DoubleEliminationBracket([1, 2, 3, 4])

    bracket.report_result("W1-1", 4)  # surprise : la tête de série 4 bat la 1

    assert bracket.matches["W2-1"].players[0] == 4
    assert bracket.matches["L1-1"].players[0] == 1


def test_report_result_errors():
    bracket = DoubleEliminationBracket([1, 2, 3, 4])

    with pytest.raises(BracketError):
        bracket.report_result("W9-9", 1)  # match inconnu
    with pytest.raises(BracketError):
        bracket.report_result("W2-1", 1)  # adversaires pas encore connus
    with pytest.raises(BracketError):
        bracket.report_result("W1-1", 2)  # 2 ne joue pas ce match

    bracket.report_result("W1-1", 1)
    with pytest.raises(BracketError):
        bracket.report_result("W1-1", 1)  # déjà joué


def test_invalid_participants():
    with pytest.raises(BracketError):
        DoubleEliminationBracket([1])
    with pytest.raises(BracketError):
        DoubleEliminationBracket([1, 2, 2])
