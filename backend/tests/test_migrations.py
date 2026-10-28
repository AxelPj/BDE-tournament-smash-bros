"""Vérifie que les migrations s'appliquent sur une base vide et correspondent
aux modèles (sinon une migration a été oubliée)."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.core.db import Base, make_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config(url: str) -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config


def test_upgrade_then_downgrade(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    config = alembic_config(url)
    engine = make_engine(url)

    command.upgrade(config, "head")
    assert {"users", "sessions"} <= set(inspect(engine).get_table_names())

    command.downgrade(config, "base")
    assert {"users", "sessions"}.isdisjoint(inspect(engine).get_table_names())
    engine.dispose()


def test_migrations_match_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    command.upgrade(alembic_config(url), "head")
    engine = make_engine(url)

    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert diff == []


def test_upgrade_preserves_existing_data(tmp_path):
    """Régression : les migrations « batch » de SQLite recréent les tables ;
    les lignes liées par clé étrangère (ON DELETE CASCADE) ne doivent pas disparaître."""
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    config = alembic_config(url)
    command.upgrade(config, "0003")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO users (id, username, display_name, is_admin) VALUES (1, 'a', 'A', 0)"
        )
        connection.exec_driver_sql(
            "INSERT INTO tournaments (id, name, format, status, registration_open) "
            "VALUES (1, 'T', 'double_elimination', 'in_progress', 0)"
        )
        connection.exec_driver_sql(
            "INSERT INTO participants (tournament_id, user_id, seed) VALUES (1, 1, 1)"
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT user_id, seed, bracket_seed FROM participants"
        ).all()
        assert rows == [(1, 1, 1)]
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    engine.dispose()
