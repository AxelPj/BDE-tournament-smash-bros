"""Cycle de vie d'un duel :

    pending ─(adversaire accepte)→ accepted ─(admin valide)→ validated
            ─(admin lance)→ in_progress ─(admin saisit le score)→ completed

    pending ─(adversaire refuse)→ refused
    pending ─(demandeur annule)→ cancelled
    tout état actif ─(admin annule)→ cancelled
"""

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.bets.service import settle_duel as settle_bets
from app.gages.service import sync_duel as sync_gages
from app.duels.models import ACTIVE_STATUSES, Duel, DuelStatus
from app.users.models import User


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class DuelStateError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _require_status(duel: Duel, *allowed: DuelStatus) -> None:
    if duel.status not in allowed:
        raise DuelStateError(f"Action impossible : le duel est « {duel.status} »")


def get_duel(db: Session, duel_id: int) -> Duel:
    duel = db.get(Duel, duel_id)
    if duel is None:
        raise NotFoundError("Duel introuvable")
    return duel


def list_duels(
    db: Session, status: DuelStatus | None = None, user_id: int | None = None
) -> list[Duel]:
    query = select(Duel).order_by(Duel.id.desc()).limit(200)
    if status is not None:
        query = query.where(Duel.status == status)
    if user_id is not None:
        query = query.where(or_(Duel.challenger_id == user_id, Duel.opponent_id == user_id))
    return list(db.scalars(query))


def create_duel(db: Session, challenger: User, opponent_id: int) -> Duel:
    if opponent_id == challenger.id:
        raise ValueError("Impossible de se défier soi-même")
    if db.get(User, opponent_id) is None:
        raise NotFoundError("Adversaire introuvable")
    pair = (challenger.id, opponent_id)
    already_active = db.scalar(
        select(Duel.id).where(
            Duel.challenger_id.in_(pair),
            Duel.opponent_id.in_(pair),
            Duel.status.in_(ACTIVE_STATUSES),
        )
    )
    if already_active:
        raise DuelStateError("Un duel est déjà en cours entre ces deux joueurs")

    duel = Duel(challenger_id=challenger.id, opponent_id=opponent_id)
    db.add(duel)
    db.commit()
    return duel


def respond(db: Session, duel: Duel, user: User, accept: bool) -> Duel:
    if user.id != duel.opponent_id:
        raise ForbiddenError("Seul le joueur défié peut répondre")
    _require_status(duel, DuelStatus.PENDING)
    duel.status = DuelStatus.ACCEPTED if accept else DuelStatus.REFUSED
    duel.responded_at = _now()
    db.commit()
    return duel


def cancel(db: Session, duel: Duel, user: User) -> Duel:
    """Le demandeur peut annuler tant que le défi n'est pas accepté ;
    un admin peut annuler un duel à tout moment avant la fin."""
    if user.is_admin:
        _require_status(duel, *ACTIVE_STATUSES)
    elif user.id == duel.challenger_id:
        _require_status(duel, DuelStatus.PENDING)
    else:
        raise ForbiddenError("Seul le demandeur ou un admin peut annuler ce duel")
    duel.status = DuelStatus.CANCELLED
    duel.cancelled_by_id = user.id
    settle_bets(db, duel)  # rembourse les paris
    sync_gages(db, duel)  # rend les gages engagés
    db.commit()
    return duel


def validate(db: Session, duel: Duel, admin: User) -> Duel:
    _require_status(duel, DuelStatus.ACCEPTED)
    duel.status = DuelStatus.VALIDATED
    duel.validated_by_id = admin.id
    duel.validated_at = _now()
    db.commit()
    return duel


def start(db: Session, duel: Duel) -> Duel:
    """Lance le duel : les paris sont fermés."""
    _require_status(duel, DuelStatus.VALIDATED)
    duel.status = DuelStatus.IN_PROGRESS
    duel.started_at = _now()
    db.commit()
    return duel


def report_result(db: Session, duel: Duel, challenger_score: int, opponent_score: int) -> Duel:
    """Saisit le score d'un duel en cours, ou corrige celui d'un duel terminé."""
    _require_status(duel, DuelStatus.IN_PROGRESS, DuelStatus.COMPLETED)
    if challenger_score == opponent_score:
        raise ValueError("Pas de match nul : il faut un vainqueur")
    duel.challenger_score = challenger_score
    duel.opponent_score = opponent_score
    duel.winner_id = (
        duel.challenger_id if challenger_score > opponent_score else duel.opponent_id
    )
    duel.status = DuelStatus.COMPLETED
    duel.completed_at = duel.completed_at or _now()
    settle_bets(db, duel)
    sync_gages(db, duel)
    db.commit()
    return duel
