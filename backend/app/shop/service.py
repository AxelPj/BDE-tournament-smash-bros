"""Boutique de gages et inventaire des joueurs."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.economy.models import TransactionKind
from app.economy.service import record_transaction
from app.shop.models import Gage, InventoryItem, InventoryStatus


class NotFoundError(Exception):
    pass


class UnavailableError(Exception):
    pass


def list_gages(db: Session, shop_only: bool, include_archived: bool = False) -> list[Gage]:
    query = select(Gage).order_by(Gage.price, Gage.name)
    if shop_only:
        query = query.where(Gage.is_available, ~Gage.is_archived)
    elif not include_archived:
        query = query.where(~Gage.is_archived)
    return list(db.scalars(query))


def get_gage(db: Session, gage_id: int) -> Gage:
    gage = db.get(Gage, gage_id)
    if gage is None:
        raise NotFoundError("Gage introuvable")
    return gage


def create_gage(db: Session, **fields) -> Gage:
    gage = Gage(**fields)
    db.add(gage)
    db.commit()
    return gage


def update_gage(db: Session, gage: Gage, **fields) -> Gage:
    for name, value in fields.items():
        setattr(gage, name, value)
    db.commit()
    return gage


def purchase(db: Session, user_id: int, gage_id: int) -> InventoryItem:
    """Débite le joueur et ajoute le gage à son inventaire, en une seule
    transaction : si l'une des deux opérations échoue, aucune n'est enregistrée."""
    gage = get_gage(db, gage_id)
    if gage.is_archived or not gage.is_available:
        raise UnavailableError("Ce gage n'est pas disponible à l'achat")

    transaction = None
    if gage.price > 0:
        # Lève InsufficientFundsError si le solde ne suffit pas.
        transaction = record_transaction(
            db, user_id, -gage.price, TransactionKind.SHOP_PURCHASE, f"Achat : {gage.name}"
        )
    item = InventoryItem(
        user_id=user_id,
        gage=gage,
        purchase_price=gage.price,
        transaction_id=transaction.id if transaction else None,
    )
    db.add(item)
    db.commit()
    return item


def list_inventory(
    db: Session, user_id: int, status: InventoryStatus | None = None
) -> list[InventoryItem]:
    query = (
        select(InventoryItem)
        .options(selectinload(InventoryItem.gage))
        .where(InventoryItem.user_id == user_id)
        .order_by(InventoryItem.id.desc())
    )
    if status is not None:
        query = query.where(InventoryItem.status == status)
    return list(db.scalars(query))
