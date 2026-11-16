import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, engine
from app.models import Account
from tests.helpers import register_user

SHEBA_1 = "IR740990000000000000000001"
SHEBA_2 = "IR470990000000000000000002"


def test_accounts_table_has_the_expected_columns(client):
    columns = {column["name"]: column for column in inspect(engine).get_columns("accounts")}
    assert set(columns) >= {"id", "user_id", "sheba_number", "status"}
    for name in ("user_id", "sheba_number", "status"):  # the primary key id can not be empty either
        assert not columns[name]["nullable"], name


def test_user_id_is_a_foreign_key_to_users(client):
    foreign_keys = inspect(engine).get_foreign_keys("accounts")
    assert any(fk["referred_table"] == "users" and fk["constrained_columns"] == ["user_id"] for fk in foreign_keys)


def test_user_id_is_indexed(client):
    indexes = inspect(engine).get_indexes("accounts")
    assert any(index["column_names"] == ["user_id"] for index in indexes)


def test_sheba_number_is_unique(client):
    user = register_user(client)
    with SessionLocal() as db:
        db.add(Account(user_id=user["id"], sheba_number=SHEBA_1))
        db.commit()
        db.add(Account(user_id=user["id"], sheba_number=SHEBA_1))
        with pytest.raises(IntegrityError):
            db.commit()


def test_status_is_one_of_the_three_allowed_values(client):
    user = register_user(client)
    with SessionLocal() as db:
        db.add(Account(user_id=user["id"], sheba_number=SHEBA_1, status="CLOSED"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_new_account_is_active_by_default_and_has_a_generated_id(client):
    user = register_user(client)
    with SessionLocal() as db:
        db.add(Account(user_id=user["id"], sheba_number=SHEBA_2))
        db.commit()
        account = db.scalar(select(Account).where(Account.sheba_number == SHEBA_2))
        assert account.status == "ACTIVE"
        assert len(account.id) == 36