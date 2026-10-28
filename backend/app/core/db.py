"""Connexion à la base de données et session SQLAlchemy."""

import sqlite3
from collections.abc import Iterator

from enum import StrEnum

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Noms de contraintes explicites : indispensable pour que les migrations
# Alembic puissent les retrouver (surtout avec SQLite).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def enum_column(enum_cls: type[StrEnum]) -> SAEnum:
    """Stocke la valeur d'une StrEnum (ex. "in_progress") dans une colonne texte."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda members: [m.value for m in members],
    )


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    """SQLite désactive les clés étrangères par défaut : on les active.
    Le mode WAL permet de lire pendant qu'une écriture est en cours."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    with SessionLocal() as session:
        yield session
