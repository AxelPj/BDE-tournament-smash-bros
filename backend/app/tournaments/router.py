from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.auth.dependencies import get_current_user, require_admin
from app.core.db import get_db
from app.game_settings.router import require_mode
from app.game_settings.service import Mode
from app.tournaments import service
from app.tournaments.bracket import Side
from app.tournaments.models import Tournament
from app.tournaments.schemas import (
    MatchRead,
    ParticipantAdd,
    ScoreReport,
    ScoreResult,
    SeedsUpdate,
    TournamentCreate,
    TournamentDetail,
    TournamentSummary,
    TournamentUpdate,
)
from app.users.models import User

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


@contextmanager
def _http_errors() -> Iterator[None]:
    """Traduit les erreurs métier en réponses HTTP."""
    try:
        yield
    except service.NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except service.TournamentStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except StaleDataError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Le tournoi a été modifié en même temps par quelqu'un d'autre : rechargez et réessayez",
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


def _get_tournament(tournament_id: int, db: Session = Depends(get_db)) -> Tournament:
    with _http_errors():
        return service.get_tournament(db, tournament_id)


# --- Consultation (publique) ---


@router.get("", response_model=list[TournamentSummary])
def list_tournaments(db: Session = Depends(get_db)):
    return [TournamentSummary.from_model(t) for t in service.list_tournaments(db)]


@router.get("/{tournament_id}", response_model=TournamentDetail)
def get_tournament(tournament: Tournament = Depends(_get_tournament)):
    return TournamentDetail.from_model(tournament)


SIDE_ORDER = {Side.WINNERS: 0, Side.LOSERS: 1, Side.GRAND_FINAL: 2}


@router.get("/{tournament_id}/matches", response_model=list[MatchRead])
def list_matches(tournament: Tournament = Depends(_get_tournament)):
    """Tous les matchs du bracket, triés : WB, LB puis grande finale."""
    return sorted(tournament.matches, key=lambda m: (SIDE_ORDER[m.side], m.round, m.position))


# --- Inscription par le joueur lui-même ---


@router.post(
    "/{tournament_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_mode(Mode.TOURNAMENTS)],
)
def register(
    tournament: Tournament = Depends(_get_tournament),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with _http_errors():
        service.add_participant(db, tournament, user.id, by_admin=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{tournament_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_mode(Mode.TOURNAMENTS)],
)
def unregister(
    tournament: Tournament = Depends(_get_tournament),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with _http_errors():
        service.remove_participant(db, tournament, user.id, by_admin=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Administration ---


@router.post("", response_model=TournamentDetail, status_code=status.HTTP_201_CREATED)
def create_tournament(
    body: TournamentCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    return TournamentDetail.from_model(service.create_tournament(db, body.name, body.rewards))


@router.patch("/{tournament_id}", response_model=TournamentDetail)
def update_tournament(
    body: TournamentUpdate,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    with _http_errors():
        service.update_tournament(
            db, tournament, body.name, body.registration_open, body.rewards
        )
    return TournamentDetail.from_model(tournament)


@router.post("/{tournament_id}/participants", response_model=TournamentDetail)
def add_participant(
    body: ParticipantAdd,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    with _http_errors():
        service.add_participant(db, tournament, body.user_id, by_admin=True)
    return TournamentDetail.from_model(tournament)


@router.delete("/{tournament_id}/participants/{user_id}", response_model=TournamentDetail)
def remove_participant(
    user_id: int,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    with _http_errors():
        service.remove_participant(db, tournament, user_id, by_admin=True)
    return TournamentDetail.from_model(tournament)


@router.put("/{tournament_id}/seeds", response_model=TournamentDetail)
def set_seeds(
    body: SeedsUpdate,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    with _http_errors():
        service.set_seeds(db, tournament, body.user_ids)
    return TournamentDetail.from_model(tournament)


@router.post("/{tournament_id}/generate", response_model=list[MatchRead])
def generate_bracket(
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    with _http_errors():
        service.generate_bracket(db, tournament)
    return list_matches(tournament)


@router.post("/{tournament_id}/reset", response_model=TournamentDetail)
def reset_bracket(
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Annule la génération du bracket, tant qu'aucun score n'a été saisi."""
    with _http_errors():
        service.reset_bracket(db, tournament)
    return TournamentDetail.from_model(tournament)


@router.put("/{tournament_id}/matches/{code}/score", response_model=ScoreResult)
def report_score(
    code: str,
    body: ScoreReport,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Saisit le score d'un match jouable, ou corrige celui d'un match déjà joué.
    score1 et score2 correspondent à player1 et player2 du match."""
    with _http_errors():
        invalidated = service.report_score(db, tournament, code, body.score1, body.score2)
    return ScoreResult(invalidated=invalidated, matches=list_matches(tournament))


@router.delete("/{tournament_id}/matches/{code}/score", response_model=ScoreResult)
def cancel_score(
    code: str,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Supprime le résultat d'un match, qui redevient à jouer."""
    with _http_errors():
        invalidated = service.cancel_score(db, tournament, code)
    return ScoreResult(invalidated=invalidated, matches=list_matches(tournament))


@router.post("/{tournament_id}/matches/{code}/start", response_model=MatchRead)
def start_match(
    code: str,
    tournament: Tournament = Depends(_get_tournament),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Lance un match : les paris sont fermés. (La saisie d'un score ferme aussi les paris.)"""
    with _http_errors():
        return service.start_match(db, tournament, code)
