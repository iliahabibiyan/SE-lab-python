import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.iban import is_valid_sheba
from app.models import Account
from app.utils import new_id
from tests.helpers import (
    NATIONAL_CODE,
    OTHER_NATIONAL_CODE,
    auth_header,
    register_other_user,
    register_user,
    token_for,
    update_user,
)

URL = "/api/v1/accounts"


def stored_accounts(user_id: str) -> list[Account]:
    with SessionLocal() as db:
        return list(db.scalars(select(Account).where(Account.user_id == user_id)))


def staff_headers(client, role: str = "ADMIN") -> dict:
    """The default user becomes staff; returns his auth header."""
    update_user(NATIONAL_CODE, role=role)
    return auth_header(token_for(client))


# ---------- success ----------
def test_customer_opens_an_account_for_himself(client):
    me = register_user(client)
    response = client.post(URL, json={"user_id": me["id"]}, headers=auth_header(token_for(client)))
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == me["id"]
    assert body["status"] == "ACTIVE"
    assert len(body["id"]) == 36


def test_the_sheba_of_the_new_account_is_valid(client):
    me = register_user(client)
    body = client.post(URL, json={"user_id": me["id"]}, headers=auth_header(token_for(client))).json()
    sheba = body["sheba_number"]
    assert is_valid_sheba(sheba)  # IR + 24 digits, ISO 13616 check
    assert sheba[4:7] == "099"  # LabBank


def test_the_new_account_is_saved_and_can_be_read_back(client):
    me = register_user(client)
    body = client.post(URL, json={"user_id": me["id"]}, headers=auth_header(token_for(client))).json()

    stored = stored_accounts(me["id"])
    assert [(a.id, a.sheba_number, a.status) for a in stored] == [(body["id"], body["sheba_number"], "ACTIVE")]

    read_back = client.get(f"{URL}/{body['id']}")  # the same account can be read with GET /accounts/{id}
    assert read_back.status_code == 200
    assert read_back.json()["sheba_number"] == body["sheba_number"]
 

def test_every_account_gets_a_different_id_and_sheba(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    bodies = [client.post(URL, json={"user_id": me["id"]}, headers=headers).json() for _ in range(3)]
    assert len({b["id"] for b in bodies}) == 3
    assert len({b["sheba_number"] for b in bodies}) == 3


@pytest.mark.parametrize("role", ["ADMIN", "MANAGER", "OFFICER"])
def test_staff_opens_an_account_for_a_customer(client, role):
    register_user(client)
    other = register_other_user(client)
    response = client.post(URL, json={"user_id": other["id"]}, headers=staff_headers(client, role))
    assert response.status_code == 201
    assert response.json()["user_id"] == other["id"]


# ---------- the owner must be an ACTIVE user ----------
@pytest.mark.parametrize("status", ["BLOCKED", "INACTIVE"])
def test_no_account_for_a_user_who_is_not_active(client, status):
    register_user(client)
    other = register_other_user(client)
    update_user(OTHER_NATIONAL_CODE, status=status)
    response = client.post(URL, json={"user_id": other["id"]}, headers=staff_headers(client))
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "USER_NOT_ACTIVE"
    assert stored_accounts(other["id"]) == []  # nothing was created


def test_blocked_user_can_not_open_an_account_for_himself(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    update_user(NATIONAL_CODE, status="BLOCKED")
    response = client.post(URL, json={"user_id": me["id"]}, headers=headers)
    assert response.status_code == 403  # a blocked user is stopped before: his token does not work any more
    assert stored_accounts(me["id"]) == []


def test_unknown_owner_is_a_404_for_staff(client):
    register_user(client)
    response = client.post(URL, json={"user_id": new_id()}, headers=staff_headers(client))
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


# ---------- who may open an account ----------
def test_customer_can_not_open_an_account_for_somebody_else(client):
    register_user(client)
    other = register_other_user(client)
    response = client.post(URL, json={"user_id": other["id"]}, headers=auth_header(token_for(client)))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert stored_accounts(other["id"]) == []


def test_customer_gets_403_even_if_the_owner_does_not_exist(client):
    register_user(client)
    response = client.post(URL, json={"user_id": new_id()}, headers=auth_header(token_for(client)))
    assert response.status_code == 403  # no hint whether the id exists


def test_opening_an_account_requires_login(client):
    me = register_user(client)
    assert client.post(URL, json={"user_id": me["id"]}).status_code == 401
    assert client.post(URL, json={"user_id": me["id"]}, headers=auth_header("not-a-jwt")).status_code == 401


# ---------- bad input ----------
def test_user_id_is_required(client):
    register_user(client)
    response = client.post(URL, json={}, headers=auth_header(token_for(client)))
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "user_id"


def test_malformed_user_id_and_extra_fields_are_rejected(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    assert client.post(URL, json={"user_id": "abc"}, headers=headers).status_code == 400
    for extra in ({"status": "BLOCKED"}, {"sheba_number": "IR000000000000000000000000"}, {"id": new_id()}):
        response = client.post(URL, json={"user_id": me["id"], **extra}, headers=headers)
        assert response.status_code == 400, extra  # the client can not choose status, Sheba or id
    assert stored_accounts(me["id"]) == []