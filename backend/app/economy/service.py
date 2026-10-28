"""Monnaie Tilt. Toute modification de solde passe par record_transaction."""

from collections import defaultdict

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.economy.models import TiltTransaction, TransactionKind
from app.users.models import User


class InsufficientFundsError(Exception):
    pass


class UnknownUserError(Exception):
    pass


def record_transaction(
    db: Session,
    user_id: int,
    amount: int,
    kind: TransactionKind,
    description: str,
    reference: str | None = None,
    created_by_id: int | None = None,
) -> TiltTransaction:
    """Crédite (amount > 0) ou débite (amount < 0) un joueur et l'inscrit au journal.

    Ne valide pas la transaction SQL (pas de commit) : l'appelant peut ainsi
    regrouper plusieurs opérations (ex. débit + ajout à l'inventaire) qui
    réussissent ou échouent ensemble.
    """
    if amount == 0:
        raise ValueError("Le montant ne peut pas être nul")
    if reference is not None:
        existing = db.scalar(select(TiltTransaction).where(TiltTransaction.reference == reference))
        if existing is not None:
            return existing

    # Une seule instruction SQL : vérifie le solde et le modifie de façon atomique,
    # même si deux requêtes arrivent en même temps.
    new_balance = db.execute(
        update(User)
        .where(User.id == user_id, User.balance + amount >= 0)
        .values(balance=User.balance + amount)
        .returning(User.balance),
        execution_options={"synchronize_session": "fetch"},
    ).scalar_one_or_none()
    if new_balance is None:
        if db.get(User, user_id) is None:
            raise UnknownUserError(f"Utilisateur introuvable : {user_id}")
        raise InsufficientFundsError("Solde de Tilt insuffisant")

    transaction = TiltTransaction(
        user_id=user_id,
        amount=amount,
        balance_after=new_balance,
        kind=kind,
        description=description,
        reference=reference,
        created_by_id=created_by_id,
    )
    db.add(transaction)
    db.flush()
    return transaction


def list_transactions(db: Session, user_id: int, limit: int, offset: int) -> list[TiltTransaction]:
    query = (
        select(TiltTransaction)
        .where(TiltTransaction.user_id == user_id)
        .order_by(TiltTransaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query))


def reconcile_credits(
    db: Session,
    prefix: str,
    desired: dict[str, tuple[int, int, str]],
    kind: TransactionKind,
    cancelled_label: str,
) -> None:
    """Aligne les versements automatiques (récompenses, gains de paris) sur ce qui est dû.

    `desired` : {clé: (joueur, montant dû, libellé)}, chaque clé commençant par `prefix`.
    On compare avec ce qui a déjà été versé pour chaque clé (transactions dont la
    référence est « clé#n ») et on verse ou reprend la différence. Ne commit pas.

    Si un joueur a déjà dépensé des Tilt qu'on doit lui reprendre, on ne reprend
    que ce qu'il a (le solde ne devient jamais négatif) ; le reste sera repris
    au prochain recalcul, si son solde le permet.
    """
    paid: dict[str, int] = defaultdict(int)
    payments: dict[str, int] = defaultdict(int)
    owner: dict[str, int] = {}
    rows = db.execute(
        select(TiltTransaction.reference, TiltTransaction.amount, TiltTransaction.user_id)
        .where(TiltTransaction.reference.like(f"{prefix}%"))
    )
    for reference, amount, user_id in rows:
        key = reference.split("#")[0]
        paid[key] += amount
        payments[key] += 1
        owner[key] = user_id

    for key in sorted(desired.keys() | paid.keys()):
        user_id, amount, label = desired.get(key, (owner.get(key), 0, cancelled_label))
        difference = amount - paid[key]
        if difference < 0:
            balance = db.scalar(select(User.balance).where(User.id == user_id))
            difference = max(difference, -balance)
        if difference == 0:
            continue
        description = label if payments[key] == 0 else f"Correction : {label}"
        record_transaction(
            db, user_id, difference, kind, description, reference=f"{key}#{payments[key] + 1}"
        )
