import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + (Path(tempfile.mkdtemp()) / "test.db").as_posix()
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["JWT_SECRET"] = "test-secret-key-only-for-unit-tests-123456"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users"))