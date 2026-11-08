from app.utils import new_id
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
)

URL = "/api/v1/users"
SENSITIVE_FIELDS = ("password", "password_hash", "failed_login_attempts", "locked_until")


def test_register_login_then_find_the_user_by_id_and_by_national_code(client):
    user = register_user(client)
    headers = auth_header(login(client).json()["access_token"])

    by_id = client.get(f"{URL}/{user['id']}", headers=headers)
    assert by_id.status_code == 200
    assert by_id.json() == user  # same data that registration returned

    by_code = client.get(URL, params={"national_code": NATIONAL_CODE}, headers=headers)
    assert by_code.status_code == 200
    assert by_code.json()["items"] == [user]


def test_unknown_user_returns_404_problem_details(client):
    register_user(client)
    make_admin(NATIONAL_CODE)  # a normal user would get 403 here, see test_access_control.py
    headers = {**auth_header(token_for(client)), "X-Correlation-ID": "it-test-404"}

    response = client.get(f"{URL}/{new_id()}", headers=headers)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 404
    assert body["code"] == "NOT_FOUND"
    assert body["correlation_id"] == "it-test-404"
    assert response.headers["X-Correlation-ID"] == "it-test-404"


def test_malformed_user_id_returns_400(client):
    register_user(client)
    response = client.get(f"{URL}/12345", headers=auth_header(token_for(client)))
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_blocked_user_can_not_read_profiles(client):
    user = register_user(client)
    headers = auth_header(token_for(client))
    update_user(NATIONAL_CODE, status="BLOCKED")  # blocked after the token was issued
    response = client.get(f"{URL}/{user['id']}", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_reads_another_users_profile(client):
    register_user(client)
    other = register_other_user(client)
    make_admin(NATIONAL_CODE)
    response = client.get(f"{URL}/{other['id']}", headers=auth_header(token_for(client)))
    assert response.status_code == 200
    assert response.json() == other


def test_cursor_pagination_walks_through_all_users(client):
    registered = [
        register_user(client),
        register_user(client, national_code=OTHER_NATIONAL_CODE, phone_number="09121234567"),
        register_user(client, national_code="1234567891", phone_number="09127654321"),
    ]
    make_admin(NATIONAL_CODE)
    headers = auth_header(token_for(client))

    first = client.get(URL, params={"limit": 2}, headers=headers).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"] == first["items"][1]["id"]

    second = client.get(URL, params={"limit": 2, "cursor": first["next_cursor"]}, headers=headers).json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None

    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == sorted(ids)  # ordered by id
    assert set(ids) == {user["id"] for user in registered}


def test_no_sensitive_field_is_ever_returned(client):
    user = register_user(client)
    make_admin(NATIONAL_CODE)
    headers = auth_header(token_for(client))
    single = client.get(f"{URL}/{user['id']}", headers=headers).json()
    listed = client.get(URL, headers=headers).json()["items"][0]
    for body in (single, listed):
        for field in SENSITIVE_FIELDS:
            assert field not in body, field