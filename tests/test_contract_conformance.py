"""The responses of the service must match openapi/account.yaml (the source of truth)."""

from fastapi.routing import APIRoute

import app.routers.accounts as accounts_router
from app.utils import new_id
from main import app
from tests.contract_helpers import CONTRACT, assert_matches_contract
from tests.helpers import (
    NATIONAL_CODE,
    OTHER_NATIONAL_CODE,
    auth_header,
    login,
    make_admin,
    register_other_user,
    register_user,
    token_for,
    update_user,
    valid_payload,
)

API = "/api/v1"


def test_every_implemented_endpoint_is_in_the_contract():
    missing = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith(API):
            continue  # /health, /ready and the documentation pages are not part of the contract
        path = route.path[len(API) :]
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if method.lower() not in CONTRACT["paths"].get(path, {}):
                missing.append(f"{method} {route.path}")
    assert not missing, f"not in openapi/account.yaml: {missing}"


def test_register_user(client):
    assert_matches_contract(client.post(f"{API}/users", json=valid_payload()), "registerUser", 201)
    assert_matches_contract(client.post(f"{API}/users", json=valid_payload()), "registerUser", 409)
    assert_matches_contract(client.post(f"{API}/users", json={}), "registerUser", 400)


def test_login_and_refresh(client):
    register_user(client)
    ok = login(client)
    assert_matches_contract(ok, "login", 200)
    assert_matches_contract(login(client, password="wrong-password"), "login", 401)
    assert_matches_contract(client.post(f"{API}/auth/login", json={}), "login", 400)
    refresh_token = ok.json()["refresh_token"]
    assert_matches_contract(
        client.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token}),
        "refreshToken",
        200,
    )
    assert_matches_contract(
        client.post(f"{API}/auth/refresh", json={"refresh_token": "not-a-jwt"}),
        "refreshToken",
        401,
    )
    for _ in range(4):  # 5 wrong passwords in total lock the account
        login(client, password="wrong-password")
    assert_matches_contract(login(client), "login", 429)


def test_login_of_a_blocked_user(client):
    register_user(client)
    update_user(NATIONAL_CODE, status="BLOCKED")
    assert_matches_contract(login(client), "login", 403)


def test_current_user(client):
    register_user(client)
    headers = auth_header(token_for(client))
    assert_matches_contract(client.get(f"{API}/auth/me", headers=headers), "getCurrentUser", 200)
    assert_matches_contract(client.get(f"{API}/auth/me"), "getCurrentUser", 401)


def test_user_endpoints_for_a_normal_user(client):
    me = register_user(client)
    other = register_other_user(client)
    headers = auth_header(token_for(client))
    new_data = {"phone_number": "09129998877", "address": "Tehran, Enghelab St., No. 5", "postal_code": "1946813561"}

    assert_matches_contract(client.get(f"{API}/users", headers=headers), "listUsers", 200)
    assert_matches_contract(client.get(f"{API}/users", params={"limit": 0}, headers=headers), "listUsers", 400)
    assert_matches_contract(client.get(f"{API}/users/{me['id']}", headers=headers), "getUser", 200)
    assert_matches_contract(client.get(f"{API}/users/{other['id']}", headers=headers), "getUser", 403)
    assert_matches_contract(client.get(f"{API}/users/not-a-uuid", headers=headers), "getUser", 400)
    assert_matches_contract(client.put(f"{API}/users/{me['id']}", json=new_data, headers=headers), "updateUser", 200)
    assert_matches_contract(client.put(f"{API}/users/{me['id']}", json={}, headers=headers), "updateUser", 400)
    assert_matches_contract(client.put(f"{API}/users/{other['id']}", json=new_data, headers=headers), "updateUser", 403)
    body = {"status": "BLOCKED"}
    assert_matches_contract(
        client.patch(f"{API}/users/{other['id']}/status", json=body, headers=headers),
        "updateUserStatus",
        403,
    )


def test_user_endpoints_for_an_admin(client):
    me = register_user(client)
    other = register_other_user(client)
    make_admin(NATIONAL_CODE)
    headers = auth_header(token_for(client))

    assert_matches_contract(client.get(f"{API}/users/{new_id()}", headers=headers), "getUser", 404)
    payload = {
        "phone_number": "09129998877",
        "address": "Tehran, Enghelab St., No. 5",
        "postal_code": "1946813561",
    }
    assert_matches_contract(
        client.put(f"{API}/users/{new_id()}", json=payload, headers=headers),
        "updateUser",
        404,
    )
    url = f"{API}/users/{other['id']}/status"
    assert_matches_contract(
        client.patch(url, json={"status": "INACTIVE", "reason": "test"}, headers=headers),
        "updateUserStatus",
        200,
    )
    assert_matches_contract(client.patch(url, json={"status": "DELETED"}, headers=headers), "updateUserStatus", 400)
    assert_matches_contract(
        client.patch(f"{API}/users/{new_id()}/status", json={"status": "BLOCKED"}, headers=headers),
        "updateUserStatus",
        404,
    )
    assert_matches_contract(
        client.patch(f"{API}/users/{me['id']}/status", json={"status": "BLOCKED"}, headers=headers),
        "updateUserStatus",
        409,
    )


def test_manager_role_is_in_the_contract(client):
    register_user(client)
    update_user(NATIONAL_CODE, role="MANAGER")
    response = client.get(f"{API}/auth/me", headers=auth_header(token_for(client)))
    assert_matches_contract(response, "getCurrentUser", 200)  # role MANAGER must be an allowed value


def test_account_endpoints(client, monkeypatch):
    me = register_user(client)
    other = register_other_user(client)
    headers = auth_header(token_for(client))

    created = client.post(f"{API}/accounts", json={"user_id": me["id"], "account_type": "SAVINGS"}, headers=headers)
    assert_matches_contract(created, "createAccount", 201)
    assert_matches_contract(
        client.post(f"{API}/accounts", json={"user_id": other["id"]}, headers=headers),
        "createAccount",
        403,
    )
    assert_matches_contract(client.post(f"{API}/accounts", json={}, headers=headers), "createAccount", 400)
    monkeypatch.setattr(accounts_router, "MAX_ACCOUNTS_PER_USER", 1)
    assert_matches_contract(
        client.post(f"{API}/accounts", json={"user_id": me["id"]}, headers=headers),
        "createAccount",
        409,
    )

    account_id = created.json()["id"]
    assert_matches_contract(client.get(f"{API}/accounts/{account_id}"), "getAccount", 200)
    assert_matches_contract(client.get(f"{API}/accounts/{new_id()}"), "getAccount", 404)
    assert_matches_contract(client.get(f"{API}/accounts/not-a-uuid"), "getAccount", 400)


def test_account_for_a_user_who_is_not_active_and_for_an_unknown_user(client):
    register_user(client)
    other = register_other_user(client)
    make_admin(NATIONAL_CODE)
    headers = auth_header(token_for(client))
    update_user(OTHER_NATIONAL_CODE, status="BLOCKED")
    assert_matches_contract(
        client.post(f"{API}/accounts", json={"user_id": other["id"]}, headers=headers),
        "createAccount",
        400,
    )
    assert_matches_contract(
        client.post(f"{API}/accounts", json={"user_id": new_id()}, headers=headers),
        "createAccount",
        404,
    )
