from datetime import timedelta

from app.tokens import _create_token, create_access_token
from tests.helpers import NATIONAL_CODE, auth_header, login, register_user, update_user

URL = "/api/v1/auth/me"


def register_and_get_token(client) -> tuple[dict, str]:
    user = register_user(client)
    return user, login(client).json()["access_token"]


def test_me_with_valid_token(client):
    user, token = register_and_get_token(client)
    response = client.get(URL, headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user["id"]
    assert body["national_code"] == NATIONAL_CODE
    assert "password_hash" not in body


def test_me_without_token(client):
    response = client.get(URL)
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "UNAUTHORIZED"


def test_me_with_garbage_token(client):
    assert client.get(URL, headers=auth_header("not-a-jwt")).status_code == 401


def test_me_with_other_auth_scheme(client):
    assert client.get(URL, headers={"Authorization": "Basic dXNlcjpwYXNz"}).status_code == 401


def test_me_with_expired_token(client):
    user, _ = register_and_get_token(client)
    expired = _create_token(user["id"], "access", timedelta(seconds=-60))
    assert client.get(URL, headers=auth_header(expired)).status_code == 401


def test_me_with_wrong_token_type(client):
    user, _ = register_and_get_token(client)
    refresh_type = _create_token(user["id"], "refresh", timedelta(minutes=5))
    assert client.get(URL, headers=auth_header(refresh_type)).status_code == 401


def test_me_with_token_of_unknown_user(client):
    token = create_access_token("00000000-0000-7000-8000-000000000000")
    assert client.get(URL, headers=auth_header(token)).status_code == 401


def test_token_stops_working_when_user_is_blocked(client):
    _, token = register_and_get_token(client)
    update_user(NATIONAL_CODE, status="BLOCKED")
    response = client.get(URL, headers=auth_header(token))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"