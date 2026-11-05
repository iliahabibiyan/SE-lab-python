from tests.helpers import NATIONAL_CODE, auth_header, login, register_user

URL = "/api/v1/users"


def register_and_get_token(client) -> tuple[dict, str]:
    user = register_user(client)
    return user, login(client).json()["access_token"]


def test_search_by_national_code(client):
    user, token = register_and_get_token(client)
    response = client.get(URL, params={"national_code": NATIONAL_CODE}, headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [user["id"]]
    assert body["next_cursor"] is None


def test_search_accepts_persian_digits(client):
    user, token = register_and_get_token(client)
    response = client.get(URL, params={"national_code": "۰۰۱۳۵۴۲۴۱۹"}, headers=auth_header(token))
    assert [item["id"] for item in response.json()["items"]] == [user["id"]]


def test_search_unknown_national_code_returns_empty_list(client):
    _, token = register_and_get_token(client)
    response = client.get(URL, params={"national_code": "0499370899"}, headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_search_with_invalid_national_code(client):
    _, token = register_and_get_token(client)
    response = client.get(URL, params={"national_code": "123"}, headers=auth_header(token))
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "national_code"


def test_search_requires_login(client):
    register_user(client)
    response = client.get(URL, params={"national_code": NATIONAL_CODE})
    assert response.status_code == 401


def test_limit_must_be_between_1_and_200(client):
    _, token = register_and_get_token(client)
    for limit in (0, 201):
        response = client.get(URL, params={"limit": limit}, headers=auth_header(token))
        assert response.status_code == 400, limit
        assert response.json()["errors"][0]["field"] == "limit"
    assert client.get(URL, params={"limit": 200}, headers=auth_header(token)).status_code == 200


def test_list_response_has_pagination_fields(client):
    user, token = register_and_get_token(client)
    body = client.get(URL, params={"limit": 1}, headers=auth_header(token)).json()
    assert set(body) == {"items", "next_cursor"}
    assert user["id"] in [item["id"] for item in body["items"]]