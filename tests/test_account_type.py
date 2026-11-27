import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Account
from tests.helpers import auth_header, register_user, token_for

URL = "/api/v1/accounts"


def stored_type(account_id: str) -> str:
    with SessionLocal() as db:
        return db.scalar(select(Account.account_type).where(Account.id == account_id))


def test_the_type_defaults_to_current(client):
    me = register_user(client)
    response = client.post(URL, json={"user_id": me["id"]}, headers=auth_header(token_for(client)))
    assert response.status_code == 201
    assert response.json()["account_type"] == "CURRENT"
    assert stored_type(response.json()["id"]) == "CURRENT"


@pytest.mark.parametrize("account_type", ["CURRENT", "SAVINGS", "DEPOSIT"])
def test_each_type_can_be_chosen(client, account_type):
    me = register_user(client)
    response = client.post(
        URL, json={"user_id": me["id"], "account_type": account_type}, headers=auth_header(token_for(client))
    )
    assert response.status_code == 201
    assert response.json()["account_type"] == account_type
    assert stored_type(response.json()["id"]) == account_type


@pytest.mark.parametrize("bad_type", ["current", "SALARY", "", None, 5])
def test_unknown_types_are_rejected(client, bad_type):
    me = register_user(client)
    response = client.post(
        URL, json={"user_id": me["id"], "account_type": bad_type}, headers=auth_header(token_for(client))
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "account_type"


def test_the_loop_endpoint_shows_the_type(client):
    me = register_user(client)
    created = client.post(
        URL, json={"user_id": me["id"], "account_type": "SAVINGS"}, headers=auth_header(token_for(client))
    ).json()
    assert client.get(f"{URL}/{created['id']}").json()["account_type"] == "SAVINGS"
