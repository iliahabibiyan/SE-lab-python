from app.utils import new_id
from tests.helpers import (
    NATIONAL_CODE,
    OTHER_NATIONAL_CODE,
    auth_header,
    make_admin,
    register_other_user,
    register_user,
    token_for,
    valid_payload,
)

URL = "/api/v1/users"


def two_users(client) -> tuple[dict, dict]:
    return register_user(client), register_other_user(client)


def test_user_can_read_own_profile(client):
    me, _ = two_users(client)
    response = client.get(f"{URL}/{me['id']}", headers=auth_header(token_for(client)))
    assert response.status_code == 200
    assert response.json()["role"] == "USER"


def test_user_can_not_read_another_profile(client):
    _, other = two_users(client)
    response = client.get(f"{URL}/{other['id']}", headers=auth_header(token_for(client)))
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "FORBIDDEN"


def test_normal_user_gets_403_even_if_the_id_does_not_exist(client):
    two_users(client)
    response = client.get(f"{URL}/{new_id()}", headers=auth_header(token_for(client)))
    assert response.status_code == 403  # same answer as for an existing profile: no hint about existence


def test_admin_can_read_any_profile(client):
    _, other = two_users(client)
    make_admin(NATIONAL_CODE)
    response = client.get(f"{URL}/{other['id']}", headers=auth_header(token_for(client)))
    assert response.status_code == 200
    assert response.json()["id"] == other["id"]


def test_normal_user_search_only_sees_himself(client):
    me, _ = two_users(client)
    headers = auth_header(token_for(client))
    by_other_code = client.get(URL, params={"national_code": OTHER_NATIONAL_CODE}, headers=headers)
    assert by_other_code.json()["items"] == []
    listing = client.get(URL, headers=headers).json()
    assert [item["id"] for item in listing["items"]] == [me["id"]]


def test_admin_can_search_and_list_everyone(client):
    me, other = two_users(client)
    make_admin(NATIONAL_CODE)
    headers = auth_header(token_for(client))
    found = client.get(URL, params={"national_code": OTHER_NATIONAL_CODE}, headers=headers).json()
    assert [item["id"] for item in found["items"]] == [other["id"]]
    listing = client.get(URL, headers=headers).json()
    assert {item["id"] for item in listing["items"]} == {me["id"], other["id"]}


def test_role_can_not_be_chosen_at_registration(client):
    response = client.post(URL, json=valid_payload(role="ADMIN"))
    assert response.status_code == 400


def test_me_returns_the_role(client):
    register_user(client)
    response = client.get("/api/v1/auth/me", headers=auth_header(token_for(client)))
    assert response.json()["role"] == "USER"