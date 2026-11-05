from tests.helpers import NATIONAL_CODE, auth_header, login, register_user

SENSITIVE_FIELDS = ("password", "password_hash", "failed_login_attempts", "locked_until")


def url(user_id: str) -> str:
    return f"/api/v1/users/{user_id}"


def register_and_get_token(client) -> tuple[dict, str]:
    user = register_user(client)
    return user, login(client).json()["access_token"]


def test_get_own_profile(client):
    user, token = register_and_get_token(client)
    response = client.get(url(user["id"]), headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user["id"]
    assert body["national_code"] == NATIONAL_CODE
    assert body["name"] == "علی رضایی"
    assert body["birth_date"] == "1995-03-21"
    assert body["status"] == "ACTIVE"
    assert body["phone_number"] == "09123456789"
    assert body["address"] == "تهران، خیابان آزادی، پلاک ۱۰"
    assert body["postal_code"] == "1593656789"


def test_response_has_no_sensitive_fields(client):
    user, token = register_and_get_token(client)
    body = client.get(url(user["id"]), headers=auth_header(token)).json()
    for field in SENSITIVE_FIELDS:
        assert field not in body, field


def test_get_user_requires_login(client):
    user = register_user(client)
    response = client.get(url(user["id"]))
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
    assert client.get(url(user["id"]), headers=auth_header("not-a-jwt")).status_code == 401


def test_get_user_with_invalid_id(client):
    _, token = register_and_get_token(client)
    response = client.get(url("not-a-uuid"), headers=auth_header(token))
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "user_id"