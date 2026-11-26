import pathlib
from datetime import date

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database import MIGRATIONS_DIR, run_migrations
from app.models import Account, User

pytestmark = pytest.mark.postgres

SHEBA = "IR740990000000000000000001"


def add_user(db, national_code="0013542419") -> User:
    user = User(
        national_code=national_code,
        name="Ali Rezaei",
        birth_date=date(1995, 3, 21),
        phone_number="09123456789",
        address="Tehran, Azadi St., No. 10",
        postal_code="1593656789",
    )
    db.add(user)
    db.commit()
    return user


def test_all_migrations_run_on_postgresql(pg_engine):
    files = sorted(path.name for path in pathlib.Path(MIGRATIONS_DIR).glob("*.sql"))
    with pg_engine.connect() as conn:
        applied = sorted(row[0] for row in conn.execute(text("SELECT filename FROM schema_migrations")))
    assert applied == files
    assert {"users", "accounts"} <= set(inspect(pg_engine).get_table_names())


def test_running_the_migrations_again_changes_nothing(pg_engine):
    run_migrations(pg_engine)
    with pg_engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM schema_migrations")).scalar()
    assert count == len(list(pathlib.Path(MIGRATIONS_DIR).glob("*.sql")))


def test_foreign_key_of_accounts_is_enforced(pg_session_factory):
    with pg_session_factory() as db:
        db.add(Account(user_id="00000000-0000-7000-8000-000000000000", sheba_number=SHEBA))  # no such user
        with pytest.raises(IntegrityError):
            db.commit()


def test_check_and_unique_constraints(pg_session_factory):
    with pg_session_factory() as db:
        user = add_user(db)
        db.add(Account(user_id=user.id, sheba_number=SHEBA, status="CLOSED"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(Account(user_id=user.id, sheba_number=SHEBA))
        db.commit()
        db.add(Account(user_id=user.id, sheba_number=SHEBA))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(User(national_code=user.national_code, name="x", birth_date=user.birth_date, phone_number="09123456789", address="Tehran, Azadi St.", postal_code="1593656789"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_row_lock_of_the_owner_makes_a_second_request_wait(pg_session_factory):
    """Task 6.4: db.get(User, id, with_for_update=True) locks the row; a second request must wait."""
    with pg_session_factory() as first, pg_session_factory() as second:
        user_id = add_user(first).id
        first.get(User, user_id, with_for_update=True)  # the lock lives until `first` ends its transaction
        with pytest.raises(OperationalError):  # nowait: do not wait, fail at once, so the test can not hang
            second.get(User, user_id, with_for_update={"nowait": True})
        second.rollback()  # PostgreSQL aborted the transaction of `second`
        first.rollback()  # lock released
        assert second.get(User, user_id, with_for_update={"nowait": True}) is not None