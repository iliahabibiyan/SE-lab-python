from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.utils import new_id
from tests.helpers import (
    NATIONAL_CODE,
    OTHER_NATIONAL_CODE,
    auth_header,
    make_admin,
    register_other_user,
    register_user,
    token_for,
)

URL = "/api/v1/users"
NEW_DATA = {
    "phone_number": "09129998877",
    "address": "تهران، خیابان انقلاب، پلاک ۵",
    "postal_code": "1946813561",
}


def stored_user(national_code: str) -> User:
    """Read a user straight from the database."""
    with SessionLocal() as db:
        return db.scalar(select(User).where(User.national_code == national_code))


def test_update_own_profile(client):
    me = register_user(client)
    response = client.put(f"{URL}/{me['id']}", json=NEW_DATA, headers=auth_header(token_for(client)))
    assert response.status_code == 200
    body = response.json()
    assert body["phone_number"] == NEW_DATA["phone_number"]
    assert body["address"] == NEW_DATA["address"]
    assert body["postal_code"] == NEW_DATA["postal_code"]
    assert body["id"] == me["id"]  # identity fields are untouched
    assert body["national_code"] == me["national_code"]
    assert body["name"] == me["name"]


def test_update_is_saved_in_the_database(client):
    me = register_user(client)
    client.put(f"{URL}/{me['id']}", json=NEW_DATA, headers=auth_header(token_for(client)))
    user = stored_user(NATIONAL_CODE)
    assert user.phone_number == NEW_DATA["phone_number"]
    assert user.address == NEW_DATA["address"]
    assert user.postal_code == NEW_DATA["postal_code"]


def test_cached_profile_is_refreshed_after_update(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    url = f"{URL}/{me['id']}"
    assert client.get(url, headers=headers).headers["X-Cache"] == "MISS"
    assert client.get(url, headers=headers).headers["X-Cache"] == "HIT"

    assert client.put(url, json=NEW_DATA, headers=headers).status_code == 200

    after = client.get(url, headers=headers)
    assert after.headers["X-Cache"] == "MISS"  # the update removed the old cached profile
    assert after.json()["phone_number"] == NEW_DATA["phone_number"]


def test_update_requires_login(client):
    me = register_user(client)
    assert client.put(f"{URL}/{me['id']}", json=NEW_DATA).status_code == 401
    assert client.put(f"{URL}/{me['id']}", json=NEW_DATA, headers=auth_header("not-a-jwt")).status_code == 401


def test_update_with_invalid_data_is_rejected_and_nothing_changes(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    cases = [
        ("phone_number", "123"),
        ("postal_code", "12345"),
        ("postal_code", "2234567890"),
        ("address", ""),
        ("address", "     "),
    ]
    for field, value in cases:
        response = client.put(f"{URL}/{me['id']}", json={**NEW_DATA, field: value}, headers=headers)
        assert response.status_code == 400, (field, value)  # the project standard (GEN-06), see the guide
        body = response.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert body["errors"][0]["field"] == field
    user = stored_user(NATIONAL_CODE)
    assert user.phone_number == me["phone_number"]
    assert user.address == me["address"]
    assert user.postal_code == me["postal_code"]


def test_update_with_missing_fields(client):
    me = register_user(client)
    response = client.put(f"{URL}/{me['id']}", json={}, headers=auth_header(token_for(client)))
    assert response.status_code == 400
    fields = {error["field"] for error in response.json()["errors"]}
    assert fields == {"phone_number", "address", "postal_code"}


def test_update_can_not_change_other_fields(client):
    me = register_user(client)
    headers = auth_header(token_for(client))
    for extra in ({"national_code": "0499370899"}, {"role": "ADMIN"}, {"status": "BLOCKED"}, {"name": "نام دیگر"}):
        response = client.put(f"{URL}/{me['id']}", json={**NEW_DATA, **extra}, headers=headers)
        assert response.status_code == 400, extra
    user = stored_user(NATIONAL_CODE)
    assert user.role == "USER"
    assert user.status == "ACTIVE"
    assert user.name == me["name"]


def test_update_accepts_persian_digits(client):
    me = register_user(client)
    payload = {**NEW_DATA, "phone_number": "۰۹۱۲۹۹۹۸۸۷۷", "postal_code": "۱۹۴۶۸۱۳۵۶۱"}
    response = client.put(f"{URL}/{me['id']}", json=payload, headers=auth_header(token_for(client)))
    assert response.status_code == 200
    assert response.json()["phone_number"] == "09129998877"
    assert response.json()["postal_code"] == "1946813561"


def test_malformed_user_id(client):
    register_user(client)
    response = client.put(f"{URL}/not-a-uuid", json=NEW_DATA, headers=auth_header(token_for(client)))
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "user_id"


# ---------- who may edit whom ----------
def test_user_can_not_edit_another_profile(client):
    register_user(client)
    other = register_other_user(client)
    response = client.put(f"{URL}/{other['id']}", json=NEW_DATA, headers=auth_header(token_for(client)))
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "FORBIDDEN"
    assert stored_user(OTHER_NATIONAL_CODE).phone_number == other["phone_number"]  # unchanged


def test_normal_user_gets_403_even_if_the_id_does_not_exist(client):
    register_user(client)
    response = client.put(f"{URL}/{new_id()}", json=NEW_DATA, headers=auth_header(token_for(client)))
    assert response.status_code == 403  # same answer as for an existing profile: no hint about existence


def test_admin_can_edit_another_profile(client):
    register_user(client)
    other = register_other_user(client)
    make_admin(NATIONAL_CODE)
    response = client.put(f"{URL}/{other['id']}", json=NEW_DATA, headers=auth_header(token_for(client)))
    assert response.status_code == 200
    assert stored_user(OTHER_NATIONAL_CODE).phone_number == NEW_DATA["phone_number"]


def test_admin_gets_404_for_unknown_user(client):
    register_user(client)
    make_admin(NATIONAL_CODE)
    response = client.put(f"{URL}/{new_id()}", json=NEW_DATA, headers=auth_header(token_for(client)))
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "NOT_FOUND"