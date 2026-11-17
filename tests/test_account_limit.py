import pytest

import app.routers.accounts as accounts_router
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


@pytest.fixture(autouse=True)
def small_limit(monkeypatch):
    monkeypatch.setattr(accounts_router, "MAX_ACCOUNTS_PER_USER", 2)


def open_account(client, headers, user_id):
    return client.post(URL, json={"user_id": user_id}, headers=headers)


def test_a_user_can_open_accounts_up_to_the_limit(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    assert open_account(client, headers, me["id"]).status_code == 201
    assert open_account(client, headers, me["id"]).status_code == 201


def test_one_account_more_than_the_limit_is_refused(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    for _ in range(2):
        open_account(client, headers, me["id"])
    response = open_account(client, headers, me["id"])
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "CONFLICT"


def test_the_limit_is_per_user(client):
    me = register_user(client)
    other = register_other_user(client)
    headers = auth_header(token_for(client))
    for _ in range(2):
        open_account(client, headers, me["id"])
    assert open_account(client, headers, me["id"]).status_code == 409

    other_headers = auth_header(token_for(client, national_code=OTHER_NATIONAL_CODE))
    assert open_account(client, other_headers, other["id"]).status_code == 201


def test_staff_can_not_pass_the_limit_either(client):
    register_user(client)
    other = register_other_user(client)
    update_user(NATIONAL_CODE, role="OFFICER")
    staff_headers = auth_header(token_for(client))
    for _ in range(2):
        assert open_account(client, staff_headers, other["id"]).status_code == 201
    assert open_account(client, staff_headers, other["id"]).status_code == 409