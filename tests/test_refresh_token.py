from datetime import timedelta

from app.tokens import _create_token, decode_token
from tests.helpers import NATIONAL_CODE, auth_header, login, register_user, update_user

URL = "/api/v1/auth/refresh"


def login_tokens(client) -> tuple[dict, dict]:
    user = register_user(client)
    return user, login(client).json()


def test_login_returns_both_tokens(client):
    user, tokens = login_tokens(client)
    assert decode_token(tokens["access_token"], "access")["sub"] == user["id"]
    assert decode_token(tokens["refresh_token"], "refresh")["sub"] == user["id"]


def test_refresh_returns_new_working_tokens(client):
    user, tokens = login_tokens(client)
    response = client.post(URL, json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["token_type"] == "bearer"
    me = client.get("/api/v1/auth/me", headers=auth_header(new_tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


def test_access_token_can_not_be_used_as_refresh_token(client):
    _, tokens = login_tokens(client)
    response = client.post(URL, json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_refresh_token_can_not_be_used_as_access_token(client):
    _, tokens = login_tokens(client)
    response = client.get("/api/v1/auth/me", headers=auth_header(tokens["refresh_token"]))
    assert response.status_code == 401


def test_expired_refresh_token(client):
    user, _ = login_tokens(client)
    expired = _create_token(user["id"], "refresh", timedelta(seconds=-60))
    response = client.post(URL, json={"refresh_token": expired})
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_garbage_refresh_token(client):
    assert client.post(URL, json={"refresh_token": "not-a-jwt"}).status_code == 401


def test_refresh_for_unknown_user(client):
    token = _create_token("00000000-0000-7000-8000-000000000000", "refresh", timedelta(days=1))
    assert client.post(URL, json={"refresh_token": token}).status_code == 401


def test_blocked_user_can_not_refresh(client):
    _, tokens = login_tokens(client)
    update_user(NATIONAL_CODE, status="BLOCKED")
    response = client.post(URL, json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_refresh_missing_field(client):
    response = client.post(URL, json={})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "refresh_token"