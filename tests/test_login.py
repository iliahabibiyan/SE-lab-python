from app.tokens import ACCESS_TOKEN_MINUTES, decode_token
from tests.helpers import NATIONAL_CODE, login, register_user, update_user

URL = "/api/v1/auth/login"


def test_login_success_returns_jwt(client):
    user = register_user(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == ACCESS_TOKEN_MINUTES * 60
    assert decode_token(body["access_token"])["sub"] == user["id"]


def test_login_accepts_persian_digits_in_national_code(client):
    register_user(client)
    assert login(client, national_code="۰۰۱۳۵۴۲۴۱۹").status_code == 200


def test_login_wrong_password(client):
    register_user(client)
    response = login(client, password="wrong-password")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "UNAUTHORIZED"


def test_unknown_user_gets_the_same_error_as_wrong_password(client):
    register_user(client)
    wrong_password = login(client, password="wrong-password").json()
    unknown_user = login(client, national_code="0499370899").json()
    assert unknown_user["status"] == wrong_password["status"] == 401
    assert unknown_user["detail"] == wrong_password["detail"]


def test_user_without_password_hash_can_not_login(client):
    register_user(client)
    update_user(NATIONAL_CODE, password_hash=None)
    assert login(client).status_code == 401


def test_blocked_user_gets_403(client):
    register_user(client)
    update_user(NATIONAL_CODE, status="BLOCKED")
    response = login(client)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_inactive_user_gets_403(client):
    register_user(client)
    update_user(NATIONAL_CODE, status="INACTIVE")
    assert login(client).status_code == 403


def test_blocked_status_is_not_revealed_with_a_wrong_password(client):
    register_user(client)
    update_user(NATIONAL_CODE, status="BLOCKED")
    assert login(client, password="wrong-password").status_code == 401


def test_login_missing_fields(client):
    response = client.post(URL, json={"national_code": NATIONAL_CODE})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "password"