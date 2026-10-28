import os
import tempfile
from pathlib import Path

# Must be set BEFORE the app is imported: tests use a throw-away SQLite file, not PostgreSQL.
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(tempfile.mkdtemp()) / "test.db").as_posix()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:  # entering the context runs the migrations
        yield test_client
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users"))
