"""Règles métier des tournois. Les routes ne font qu'appeler ces fonctions."""

import random
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.bets.service import settle_tournament as settle_bets
from app.gages.service import sync_tournament as sync_gages
from app.tournaments.bracket import DoubleEliminationBracket, MatchStatus
from app.tournaments.models import (
    Participant,
    Tournament,
    TournamentMatch,
    TournamentStatus,
)
from app.tournaments.rewards import RewardSettings, reconcile_rewards
from app.tournaments.seeding import seed_participants
from app.users.models import User


class NotFoundError(Exception):
    pass


class TournamentStateError(Exception):
    """Action impossible dans l'état actuel du tournoi (ex. inscription après génération)."""


def list_tournaments(db: Session) -> list[Tournament]:
    query = (
        select(Tournament)
        .options(selectinload(Tournament.participants))
        .order_by(Tournament.created_at.desc(), Tournament.id.desc())
    )
    return list(db.scalars(query))


def get_tournament(db: Session, tournament_id: int) -> Tournament:
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise NotFoundError("Tournoi introuvable")
    return tournament


def create_tournament(
    db: Session, name: str, rewards: RewardSettings | None = None
) -> Tournament:
    tournament = Tournament(
        name=name.strip(), reward_settings=(rewards or RewardSettings()).model_dump()
    )
    db.add(tournament)
    db.commit()
    return tournament


def update_tournament(
    db: Session,
    tournament: Tournament,
    name: str | None,
    registration_open: bool | None,
    rewards: RewardSettings | None = None,
) -> Tournament:
    if name is not None:
        tournament.name = name.strip()
    if registration_open is not None:
        _require_registration_phase(tournament)
        tournament.registration_open = registration_open
    if rewards is not None:
        tournament.reward_settings = rewards.model_dump()
        # Les récompenses déjà versées sont ajustées aux nouveaux montants.
        reconcile_rewards(db, tournament)
    db.commit()
    return tournament


def _require_registration_phase(tournament: Tournament) -> None:
    if tournament.status is not TournamentStatus.REGISTRATION:
        raise TournamentStateError("Le bracket a déjà été généré")


def _find_participant(tournament: Tournament, user_id: int) -> Participant | None:
    return next((p for p in tournament.participants if p.user_id == user_id), None)


def add_participant(db: Session, tournament: Tournament, user_id: int, by_admin: bool) -> None:
    _require_registration_phase(tournament)
    if not by_admin and not tournament.registration_open:
        raise TournamentStateError("Les inscriptions sont fermées")
    if db.get(User, user_id) is None:
        raise NotFoundError("Utilisateur introuvable")
    if _find_participant(tournament, user_id):
        raise TournamentStateError("Déjà inscrit")
    tournament.participants.append(Participant(user_id=user_id))
    db.commit()


def remove_participant(db: Session, tournament: Tournament, user_id: int, by_admin: bool) -> None:
    _require_registration_phase(tournament)
    if not by_admin and not tournament.registration_open:
        raise TournamentStateError("Les inscriptions sont fermées")
    participant = _find_participant(tournament, user_id)
    if participant is None:
        raise NotFoundError("Pas inscrit à ce tournoi")
    tournament.participants.remove(participant)
    db.commit()


def _clear_seeds(db: Session, tournament: Tournament) -> None:
    # Remise à zéro avant réattribution : évite un conflit temporaire
    # sur la contrainte d'unicité (tournoi, tête de série).
    for participant in tournament.participants:
        participant.seed = None
    db.flush()


def set_seeds(db: Session, tournament: Tournament, user_ids: list[int]) -> None:
    """Fixe les têtes de série : user_ids[0] est n°1, etc. Les joueurs absents
    de la liste n'ont pas de tête de série et seront tirés au sort."""
    _require_registration_phase(tournament)
    if len(set(user_ids)) != len(user_ids):
        raise ValueError("Un joueur apparaît plusieurs fois")
    by_user = {p.user_id: p for p in tournament.participants}
    unknown = set(user_ids) - by_user.keys()
    if unknown:
        raise ValueError(f"Joueurs non inscrits : {sorted(unknown)}")

    _clear_seeds(db, tournament)
    for rank, user_id in enumerate(user_ids, start=1):
        by_user[user_id].seed = rank
    db.commit()


def generate_bracket(db: Session, tournament: Tournament, rng: random.Random | None = None) -> None:
    """Place les joueurs (têtes de série puis tirage au sort), construit le bracket
    et enregistre tous ses matchs. Les inscriptions sont alors figées."""
    _require_registration_phase(tournament)
    participants = tournament.participants
    if len(participants) < 2:
        raise TournamentStateError("Il faut au moins 2 participants")

    seeded = [p.user_id for p in sorted(participants, key=lambda p: p.seed or 0) if p.seed]
    order = seed_participants([p.user_id for p in participants], seeded, rng)

    by_user = {p.user_id: p for p in participants}
    for rank, user_id in enumerate(order, start=1):
        by_user[user_id].bracket_seed = rank

    bracket = DoubleEliminationBracket(order)
    tournament.matches = [
        TournamentMatch(
            code=match.id, side=match.side, round=match.round, position=match.position,
            status=match.status,
        )
        for match in bracket.matches.values()
    ]
    _write_bracket_state(tournament, bracket)
    tournament.registration_open = False
    tournament.version += 1
    reconcile_rewards(db, tournament)
    db.commit()


def reset_bracket(db: Session, tournament: Tournament) -> None:
    """Annule la génération (retour aux inscriptions), tant qu'aucun score n'est saisi.
    Les têtes de série choisies par l'admin sont conservées."""
    if tournament.status is TournamentStatus.REGISTRATION:
        raise TournamentStateError("Le bracket n'a pas été généré")
    if any(m.result_order is not None for m in tournament.matches):
        raise TournamentStateError("Des scores ont déjà été saisis")

    tournament.matches = []
    for participant in tournament.participants:
        participant.bracket_seed = None
    tournament.status = TournamentStatus.REGISTRATION
    tournament.champion_id = None
    tournament.version += 1
    sync_gages(db, tournament)  # rend les gages engagés
    reconcile_rewards(db, tournament)  # reprend la récompense de participation
    settle_bets(db, tournament)  # rembourse les paris
    db.commit()


# --- Scores ---


def _get_match(tournament: Tournament, code: str) -> TournamentMatch:
    if tournament.status is TournamentStatus.REGISTRATION:
        raise TournamentStateError("Le bracket n'a pas été généré")
    match = next((m for m in tournament.matches if m.code == code), None)
    if match is None:
        raise NotFoundError(f"Match introuvable : {code}")
    return match


def report_score(
    db: Session, tournament: Tournament, code: str, score1: int, score2: int
) -> list[str]:
    """Saisit (ou corrige) le score d'un match. Renvoie les codes des matchs
    dont le résultat a dû être annulé parce que la correction a changé leurs joueurs."""
    match = _get_match(tournament, code)
    if score1 == score2:
        raise ValueError("Pas de match nul : il faut un vainqueur")

    if match.status is MatchStatus.READY:
        orders = [m.result_order for m in tournament.matches if m.result_order is not None]
        match.result_order = max(orders, default=0) + 1
        match.started_at = match.started_at or datetime.now(UTC)  # ferme les paris
    elif match.result_order is None:
        # En attente d'adversaires, validé automatiquement (bye) ou finale reset inutile.
        raise TournamentStateError(f"Le match {code} n'est pas jouable")

    match.score1, match.score2 = score1, score2
    match.winner_id = match.player1_id if score1 > score2 else match.player2_id
    return _replay(db, tournament)


def start_match(db: Session, tournament: Tournament, code: str) -> TournamentMatch:
    """Lance un match : les paris sont fermés."""
    match = _get_match(tournament, code)
    if match.status is not MatchStatus.READY:
        raise TournamentStateError(f"Le match {code} n'est pas jouable")
    if match.started_at is not None:
        raise TournamentStateError(f"Le match {code} est déjà lancé")
    match.started_at = datetime.now(UTC)
    tournament.version += 1
    db.commit()
    return match


def cancel_score(db: Session, tournament: Tournament, code: str) -> list[str]:
    """Supprime le résultat d'un match (il redevient à jouer)."""
    match = _get_match(tournament, code)
    if match.result_order is None:
        raise TournamentStateError(f"Aucun score saisi pour le match {code}")
    _clear_result(match)
    return _replay(db, tournament)


def _clear_result(match: TournamentMatch) -> None:
    match.score1 = match.score2 = match.winner_id = match.result_order = None


def _replay(db: Session, tournament: Tournament) -> list[str]:
    """Reconstruit le bracket depuis les têtes de série en rejouant les résultats
    saisis, dans leur ordre de saisie. Un résultat n'est conservé que si le match
    oppose toujours les mêmes joueurs aux mêmes places ; sinon il est annulé."""
    order = [p.user_id for p in sorted(tournament.participants, key=lambda p: p.bracket_seed)]
    bracket = DoubleEliminationBracket(order)
    previous_players = {m.code: (m.player1_id, m.player2_id) for m in tournament.matches}

    results = sorted(
        (m for m in tournament.matches if m.result_order is not None),
        key=lambda m: m.result_order,
    )
    invalidated = []
    for row in results:
        match = bracket.matches[row.code]
        same_players = match.players == [row.player1_id, row.player2_id]
        if match.status is MatchStatus.READY and same_players:
            bracket.report_result(row.code, row.winner_id)
        else:
            _clear_result(row)
            invalidated.append(row.code)

    _write_bracket_state(tournament, bracket)
    for row in tournament.matches:
        if row.result_order is None and (row.player1_id, row.player2_id) != previous_players[row.code]:
            row.started_at = None  # nouvelle affiche : les paris rouvrent
    tournament.version += 1
    sync_gages(db, tournament)
    reconcile_rewards(db, tournament)
    settle_bets(db, tournament)
    db.commit()
    return invalidated


def _write_bracket_state(tournament: Tournament, bracket: DoubleEliminationBracket) -> None:
    """Recopie en base l'état calculé par le moteur."""
    for row in tournament.matches:
        match = bracket.matches[row.code]
        row.player1_id, row.player2_id = match.players
        row.winner_id = match.winner
        row.status = match.status
    tournament.champion_id = bracket.champion
    tournament.status = (
        TournamentStatus.COMPLETED if bracket.champion else TournamentStatus.IN_PROGRESS
    )
