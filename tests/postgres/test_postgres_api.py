import pytest
from sqlalchemy import select

import app.routers.accounts as accounts_router
from app.iban import is_valid_sheba
from app.models import Account
from tests.helpers import auth_header, login, valid_payload

pytestmark = pytest.mark.postgres


def test_register_login_and_open_accounts_on_postgresql(pg_client, pg_session_factory, monkeypatch):
    monkeypatch.setattr(accounts_router, "MAX_ACCOUNTS_PER_USER", 2)
    user = pg_client.post("/api/v1/users", json=valid_payload()).json()
    token = login(pg_client).json()["access_token"]
    headers = auth_header(token)

    first = pg_client.post("/api/v1/accounts", json={"user_id": user["id"]}, headers=headers)
    second = pg_client.post("/api/v1/accounts", json={"user_id": user["id"], "account_type": "SAVINGS"}, headers=headers)
    third = pg_client.post("/api/v1/accounts", json={"user_id": user["id"]}, headers=headers)

    assert (first.status_code, second.status_code, third.status_code) == (201, 201, 409)
    assert is_valid_sheba(first.json()["sheba_number"])
    with pg_session_factory() as db:
        accounts = list(db.scalars(select(Account).where(Account.user_id == user["id"])))
    assert len(accounts) == 2
    assert len({a.sheba_number for a in accounts}) == 2
    assert {a.account_type for a in accounts} == {"CURRENT", "SAVINGS"}


def test_duplicate_national_code_is_refused_by_postgresql(pg_client):
    assert pg_client.post("/api/v1/users", json=valid_payload()).status_code == 201
    response = pg_client.post("/api/v1/users", json=valid_payload())
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"