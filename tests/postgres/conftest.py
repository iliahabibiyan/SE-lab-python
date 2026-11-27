import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db, run_migrations
from main import app


@pytest.fixture(scope="session")
def pg_engine():
    """A real PostgreSQL 16 in a container (Docker must run). The tests are skipped when it can not start."""
    try:
        from testcontainers.postgres import PostgresContainer

        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as error:  # Docker is not running, the image can not be pulled, the package is missing, ...
        pytest.skip(f"PostgreSQL container is not available: {error}")
    engine = create_engine(container.get_connection_url(), pool_pre_ping=True)
    run_migrations(engine)  # the same SQL files the service runs at start
    yield engine
    engine.dispose()
    container.stop()


@pytest.fixture
def pg_session_factory(pg_engine):
    yield sessionmaker(bind=pg_engine, autoflush=False)
    with pg_engine.begin() as conn:
        conn.execute(text("DELETE FROM accounts"))
        conn.execute(text("DELETE FROM users"))


@pytest.fixture
def pg_client(pg_session_factory):
    """The real application, but its database is the PostgreSQL container."""

    def get_pg_db():
        db = pg_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_pg_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)