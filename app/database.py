import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://labbank:labbank@localhost:5432/s1_accounts",
)
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """Run every migrations/*.sql file (sorted by name) that has not been applied yet."""
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (filename VARCHAR(255) PRIMARY KEY)"))
        done = {row[0] for row in conn.execute(text("SELECT filename FROM schema_migrations"))}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            for statement in path.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    conn.exec_driver_sql(statement)
            conn.execute(text("INSERT INTO schema_migrations (filename) VALUES (:f)"), {"f": path.name})