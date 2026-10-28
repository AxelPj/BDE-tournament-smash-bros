import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import Base, get_db, make_engine
from app.main import app


@pytest.fixture
def engine(tmp_path):
    """Base SQLite neuve (fichier temporaire) pour chaque test."""
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db):
    """Client HTTP de test branché sur la base temporaire. Il garde les cookies
    entre deux requêtes, comme un navigateur."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
