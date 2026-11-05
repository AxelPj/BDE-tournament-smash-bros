from collections import Counter
import re

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.duels.models import Duel, DuelStatus
from app.economy.models import TransactionKind
from app.economy.service import record_transaction
from app.tournaments.bracket import MatchStatus
from app.tournaments.models import Participant, TournamentMatch
from app.users.models import User
from app.users.schemas import UserStatsRead

WELCOME_BONUS = 100


class UsernameTakenError(Exception):
    pass


def normalize_username(username: str) -> str:
    """Les identifiants sont insensibles à la casse : "Mario" == "mario"."""
    return username.strip().lower()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == normalize_username(username)))


def get_user_by_intra_id(db: Session, intra_id: int) -> User | None:
    return db.scalar(select(User).where(User.intra_id == intra_id))


def create_user(
    db: Session,
    username: str,
    display_name: str,
    intra_id: int | None = None,
    is_admin: bool = False,
) -> User:
    user = User(
        username=normalize_username(username),
        display_name=display_name.strip(),
        intra_id=intra_id,
        is_admin=is_admin,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UsernameTakenError(user.username) from exc
    return user


def make_unique_username(db: Session, username_hint: str) -> str:
    """Génère un pseudo unique (<= 32 caractères) à partir du login 42."""
    base = re.sub(r"[^a-zA-Z0-9_-]", "_", username_hint).strip("_").lower()
    if not base:
        base = "user"
    base = base[:32]
    username = base
    suffix = 1
    while get_user_by_username(db, username) is not None:
        suffix += 1
        suffix_str = f"_{suffix}"
        username = f"{base[:32 - len(suffix_str)]}{suffix_str}"
    return username


def get_or_create_42_user(
    db: Session,
    intra_id: int,
    login: str,
    display_name: str,
    avatar_url: str | None = None,
) -> User:
    """Récupère l'étudiant via son intra_id (ou lie un compte pré-créé par la CLI),
    ou l'inscrit automatiquement dans la table users."""
    user = get_user_by_intra_id(db, intra_id)
    if user is not None:
        # La photo 42 suit l'intra, sauf si le joueur a choisi un combattant
        # (chemin local /fighters/...) : son choix n'est pas écrasé à la reconnexion.
        chose_fighter = (user.avatar_url or "").startswith("/fighters/")
        if avatar_url and not chose_fighter and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)
        _grant_welcome_bonus(db, user)
        return user

    clean_display = display_name.strip() or login.strip()

    # Si un compte avec ce login 42 a été pré-créé sans intra_id (ex: via la CLI create-admin),
    # on lui associe son intra_id lors de sa première connexion 42.
    existing = get_user_by_username(db, login)
    if existing is not None and existing.intra_id is None:
        existing.intra_id = intra_id
        if avatar_url:
            existing.avatar_url = avatar_url
        if existing.display_name == existing.username and clean_display:
            existing.display_name = clean_display[:64]
        db.commit()
        db.refresh(existing)
        _grant_welcome_bonus(db, existing)
        return existing

    username = make_unique_username(db, login)
    user = User(
        username=username,
        display_name=clean_display[:64],
        intra_id=intra_id,
        avatar_url=avatar_url,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_by_intra = get_user_by_intra_id(db, intra_id)
        if existing_by_intra is not None:
            _grant_welcome_bonus(db, existing_by_intra)
            return existing_by_intra
        raise
    db.refresh(user)
    _grant_welcome_bonus(db, user)
    return user


def _grant_welcome_bonus(db: Session, user: User) -> None:
    """Crédite une seule fois le bonus du premier compte OAuth."""
    record_transaction(
        db,
        user.id,
        WELCOME_BONUS,
        TransactionKind.WELCOME_BONUS,
        "Bonus de bienvenue",
        reference=f"welcome-bonus:user:{user.id}",
    )
    db.commit()


def list_leaderboard(db: Session) -> list[UserStatsRead]:
    """Calcule le classement complet et les statistiques de tous les joueurs
    en quelques requêtes SQL GROUP BY natives (aucun N+1)."""
    win_counts: Counter[int] = Counter()
    loss_counts: Counter[int] = Counter()
    tourney_counts: Counter[int] = Counter()

    # Victoires en tournoi
    for wid, cnt in db.execute(
        select(TournamentMatch.winner_id, func.count(TournamentMatch.id))
        .where(
            TournamentMatch.status == MatchStatus.COMPLETED,
            TournamentMatch.result_order.is_not(None),
            TournamentMatch.winner_id.is_not(None),
        )
        .group_by(TournamentMatch.winner_id)
    ):
        win_counts[wid] += cnt

    # Défaites en tournoi
    t_loser_expr = case(
        (TournamentMatch.winner_id == TournamentMatch.player1_id, TournamentMatch.player2_id),
        else_=TournamentMatch.player1_id,
    )
    for lid, cnt in db.execute(
        select(t_loser_expr, func.count(TournamentMatch.id))
        .where(
            TournamentMatch.status == MatchStatus.COMPLETED,
            TournamentMatch.result_order.is_not(None),
            TournamentMatch.winner_id.is_not(None),
        )
        .group_by(t_loser_expr)
    ):
        if lid is not None:
            loss_counts[lid] += cnt

    # Victoires en duel
    for wid, cnt in db.execute(
        select(Duel.winner_id, func.count(Duel.id))
        .where(
            Duel.status == DuelStatus.COMPLETED,
            Duel.winner_id.is_not(None),
        )
        .group_by(Duel.winner_id)
    ):
        win_counts[wid] += cnt

    # Défaites en duel
    d_loser_expr = case(
        (Duel.winner_id == Duel.challenger_id, Duel.opponent_id),
        else_=Duel.challenger_id,
    )
    for lid, cnt in db.execute(
        select(d_loser_expr, func.count(Duel.id))
        .where(
            Duel.status == DuelStatus.COMPLETED,
            Duel.winner_id.is_not(None),
        )
        .group_by(d_loser_expr)
    ):
        if lid is not None:
            loss_counts[lid] += cnt

    # Participations aux tournois
    for uid, cnt in db.execute(
        select(Participant.user_id, func.count(Participant.id)).group_by(Participant.user_id)
    ):
        tourney_counts[uid] = cnt

    all_users = list(
        db.scalars(
            select(User).where(
                ~User.username.startswith("bot_"),
                ~User.username.startswith("cpu_"),
                ~User.username.startswith("pnj_"),
            )
        )
    )
    sorted_users = sorted(
        all_users,
        key=lambda u: (win_counts[u.id], u.balance, -u.id),
        reverse=True,
    )

    return [
        UserStatsRead(
            id=u.id,
            login=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            is_admin=u.is_admin,
            campus="42",
            wins=win_counts[u.id],
            losses=loss_counts[u.id],
            tournaments=tourney_counts[u.id],
            rank=idx + 1,
            balance=u.balance,
        )
        for idx, u in enumerate(sorted_users)
    ]


def get_user_stats(db: Session, user: User) -> UserStatsRead:
    """Calcule les statistiques d'un joueur à partir du classement SQL."""
    board = list_leaderboard(db)
    found = next((s for s in board if s.id == user.id), None)
    if found is not None:
        return found
    return UserStatsRead(
        id=user.id,
        login=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
        campus="42",
        wins=0,
        losses=0,
        tournaments=0,
        rank=1,
        balance=user.balance,
    )
