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
    """Optimise SQLite pour la concurrence (50+ connexions simultanées) :
    - foreign_keys=ON : intégrité référentielle stricte
    - journal_mode=WAL : lectures et écriture simultanées non bloquantes
    - busy_timeout=30000 : attend jusqu'à 30s qu'un verrou d'écriture se libère
    - synchronous=NORMAL : sûreté transactionnelle avec débit maximal en mode WAL
    - temp_store=MEMORY & cache_size=-64000 : tris et index en RAM (64 Mo)"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=-64000")
        try:
            cols = [r[1] for r in cursor.execute("PRAGMA table_info(gages)").fetchall()]
            if cols and "reward" not in cols:
                cursor.execute("ALTER TABLE gages ADD COLUMN reward INTEGER NOT NULL DEFAULT 50")
                dbapi_connection.commit()
        except sqlite3.OperationalError:
            pass
        cursor.close()


def make_engine(url: str) -> Engine:
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    return create_engine(
        url,
        connect_args=connect_args,
        pool_size=25,
        max_overflow=50,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    with SessionLocal() as session:
        yield session
