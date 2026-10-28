from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.bets import service
from app.bets.models import Bet
from app.bets.schemas import BetCreate, BetRead, MarketRead, PlayerOdds
from app.core.db import get_db
from app.duels.models import Duel
from app.duels.router import _get_duel
from app.economy.service import InsufficientFundsError
from app.game_settings.router import require_mode
from app.game_settings.service import Mode
from app.matchups import Outcome
from app.tournaments.models import Tournament
from app.tournaments.router import _get_tournament
from app.users.models import User

router = APIRouter(tags=["bets"])


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except (service.BettingClosedError, InsufficientFundsError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except service.ForbiddenBetError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


def _market(bets: list[Bet], outcome: Outcome) -> MarketRead:
    total, staked = service.market(bets, outcome)
    return MarketRead(
        betting_open=outcome.open,
        total=total,
        players=[
            PlayerOdds(user_id=player, staked=amount, odds=round(total / amount, 2) if amount else None)
            for player, amount in staked.items()
        ],
    )


def _bet_read(bet: Bet, bet_status: str, payout: int | None) -> BetRead:
    return BetRead(
        id=bet.id,
        duel_id=bet.duel_id,
        tournament_id=bet.tournament_id,
        match_code=bet.match_code,
        picked_player_id=bet.picked_player_id,
        opponent_id=bet.opponent_id,
        amount=bet.amount,
        created_at=bet.created_at,
        status=bet_status,
        payout=payout,
    )


# --- Duels ---


@router.get("/api/duels/{duel_id}/bets", response_model=MarketRead)
def duel_market(duel: Duel = Depends(_get_duel), db: Session = Depends(get_db)):
    """Total misé et cote de chaque joueur."""
    return _market(service.duel_bets(db, duel), service.duel_outcome(duel))


@router.post(
    "/api/duels/{duel_id}/bets",
    response_model=BetRead,
    status_code=201,
    dependencies=[require_mode(Mode.BETS)],
)
def bet_on_duel(
    body: BetCreate,
    duel: Duel = Depends(_get_duel),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with _http_errors():
        bet = service.place_duel_bet(db, user, duel, body.picked_player_id, body.amount)
    return _bet_read(bet, "open", None)


# --- Matchs de tournoi ---


@router.get("/api/tournaments/{tournament_id}/matches/{code}/bets", response_model=MarketRead)
def match_market(
    code: str, tournament: Tournament = Depends(_get_tournament), db: Session = Depends(get_db)
):
    """Total misé et cote de chaque joueur."""
    return _market(service.match_bets(db, tournament, code), service.match_outcome(tournament, code))


@router.post(
    "/api/tournaments/{tournament_id}/matches/{code}/bets",
    response_model=BetRead,
    status_code=201,
    dependencies=[require_mode(Mode.BETS)],
)
def bet_on_match(
    code: str,
    body: BetCreate,
    tournament: Tournament = Depends(_get_tournament),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with _http_errors():
        bet = service.place_match_bet(db, user, tournament, code, body.picked_player_id, body.amount)
    return _bet_read(bet, "open", None)


# --- Historique ---


@router.get("/api/bets/mine", response_model=list[BetRead])
def my_bets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Paris du joueur connecté, avec leur statut et le montant reçu."""
    return [_bet_read(*row) for row in service.my_bets(db, user)]
