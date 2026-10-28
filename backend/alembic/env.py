"""Exécution des migrations Alembic.

L'URL de la base vient de DATABASE_URL (config de l'app), sauf si elle est
fournie explicitement via la config Alembic (utilisé par les tests).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.core.db import Base
import app.models  # noqa: F401  (enregistre tous les modèles dans Base.metadata)

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        if connection.dialect.name == "sqlite":
            # Le mode batch recrée les tables (copie, suppression, renommage).
            # Avec les clés étrangères actives, supprimer l'ancienne table
            # effacerait en cascade les lignes qui la référencent.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            # Clôt la transaction ouverte par le PRAGMA, sinon Alembic croit
            # qu'une transaction extérieure existe et ne valide pas les migrations.
            connection.commit()
        # render_as_batch : SQLite ne sait pas modifier une colonne en place,
        # Alembic recrée alors la table de façon transparente.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
