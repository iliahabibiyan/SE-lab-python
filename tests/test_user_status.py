import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Account, User
from app.utils import new_id
from tests.helpers import (
    NATIONAL_CODE,
    OTHER_NATIONAL_CODE,
    PASSWORD,
    auth_header,
    login,
    register_other_user,
    register_user,
    token_for,
    update_user,
)

URL = "/api/v1/users"


def status_url(user_id: str) -> str:
    return f"{URL}/{user_id}/status"


def stored_user(national_code: str) -> User:
    with SessionLocal() as db:
        return db.scalar(select(User).where(User.national_code == national_code))


def create_account(user_id: str, sheba: str, status: str) -> str:
    with SessionLocal() as db:
        account = Account(user_id=user_id, sheba_number=sheba, status=status)
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.id


def staff_and_target(client, role: str = "ADMIN"):
    """The default user gets `role`; a normal second user is the target. Returns (staff_headers, target)."""
    register_user(client)
    target = register_other_user(client)
    update_user(NATIONAL_CODE, role=role)
    return auth_header(token_for(client)), target


# ---------- successful changes ----------
def test_admin_blocks_a_user(client):
    headers, target = staff_and_target(client)
    response = client.patch(status_url(target["id"]), json={"status": "BLOCKED", "reason": "court order"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "BLOCKED"
    assert response.json()["id"] == target["id"]
    assert stored_user(OTHER_NATIONAL_CODE).status == "BLOCKED"


@pytest.mark.parametrize("role", ["ADMIN", "MANAGER", "OFFICER"])
@pytest.mark.parametrize("new_status", ["INACTIVE", "BLOCKED"])
def test_every_staff_role_can_change_the_status(client, role, new_status):
    headers, target = staff_and_target(client, role)
    response = client.patch(status_url(target["id"]), json={"status": new_status}, headers=headers)
    assert response.status_code == 200
    assert stored_user(OTHER_NATIONAL_CODE).status == new_status


def test_status_can_go_back_to_active(client):
    headers, target = staff_and_target(client)
    client.patch(status_url(target["id"]), json={"status": "BLOCKED"}, headers=headers)
    response = client.patch(status_url(target["id"]), json={"status": "ACTIVE"}, headers=headers)
    assert response.status_code == 200
    assert stored_user(OTHER_NATIONAL_CODE).status == "ACTIVE"


def test_same_status_is_accepted_and_changes_nothing(client):
    headers, target = staff_and_target(client)
    response = client.patch(status_url(target["id"]), json={"status": "ACTIVE"}, headers=headers)
    assert response.status_code == 200
    assert stored_user(OTHER_NATIONAL_CODE).token_version == 0  # nothing was revoked


def test_other_users_are_not_touched(client):
    headers, target = staff_and_target(client)
    client.patch(status_url(target["id"]), json={"status": "BLOCKED"}, headers=headers)
    assert stored_user(NATIONAL_CODE).status == "ACTIVE"


def test_reason_is_optional_and_trimmed(client):
    headers, target = staff_and_target(client)
    for payload in ({"status": "INACTIVE"}, {"status": "ACTIVE", "reason": "   "}, {"status": "INACTIVE", "reason": " ok "}):
        assert client.patch(status_url(target["id"]), json=payload, headers=headers).status_code == 200


# ---------- who may call it ----------
def test_normal_user_can_not_change_a_status(client):
    register_user(client)
    target = register_other_user(client)
    response = client.patch(status_url(target["id"]), json={"status": "BLOCKED"}, headers=auth_header(token_for(client)))
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "FORBIDDEN"
    assert stored_user(OTHER_NATIONAL_CODE).status == "ACTIVE"


def test_normal_user_gets_403_even_for_an_unknown_id(client):
    register_user(client)
    response = client.patch(status_url(new_id()), json={"status": "BLOCKED"}, headers=auth_header(token_for(client)))
    assert response.status_code == 403


def test_status_change_requires_login(client):
    target = register_user(client)
    assert client.patch(status_url(target["id"]), json={"status": "BLOCKED"}).status_code == 401
    assert client.patch(status_url(target["id"]), json={"status": "BLOCKED"}, headers=auth_header("not-a-jwt")).status_code == 401


def test_staff_can_not_change_his_own_status(client):
    register_user(client)
    me = stored_user(NATIONAL_CODE)
    update_user(NATIONAL_CODE, role="ADMIN")
    response = client.patch(status_url(me.id), json={"status": "BLOCKED"}, headers=auth_header(token_for(client)))
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    assert stored_user(NATIONAL_CODE).status == "ACTIVE"


# ---------- validation ----------
@pytest.mark.parametrize("bad_status", ["DELETED", "active", "Blocked", "", None, 5, ["BLOCKED"]])
def test_invalid_status_values_are_rejected(client, bad_status):
    headers, target = staff_and_target(client)
    response = client.patch(status_url(target["id"]), json={"status": bad_status}, headers=headers)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "status"
    assert stored_user(OTHER_NATIONAL_CODE).status == "ACTIVE"


def test_missing_status_and_extra_fields_are_rejected(client):
    headers, target = staff_and_target(client)
    assert client.patch(status_url(target["id"]), json={}, headers=headers).status_code == 400
    for extra in ({"role": "ADMIN"}, {"name": "x"}, {"token_version": 5}):
        response = client.patch(status_url(target["id"]), json={"status": "BLOCKED", **extra}, headers=headers)
        assert response.status_code == 400, extra
    assert stored_user(OTHER_NATIONAL_CODE).status == "ACTIVE"


def test_too_long_reason_is_rejected(client):
    headers, target = staff_and_target(client)
    response = client.patch(status_url(target["id"]), json={"status": "BLOCKED", "reason": "x" * 256}, headers=headers)
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "reason"


def test_malformed_user_id_is_rejected(client):
    headers, _ = staff_and_target(client)
    response = client.patch(status_url("not-a-uuid"), json={"status": "BLOCKED"}, headers=headers)
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "user_id"


def test_staff_gets_404_for_an_unknown_user(client):
    headers, _ = staff_and_target(client)
    response = client.patch(status_url(new_id()), json={"status": "BLOCKED"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


# ---------- what the new status means for the user ----------
def test_blocked_user_can_not_log_in_until_activated(client):
    headers, target = staff_and_target(client)
    client.patch(status_url(target["id"]), json={"status": "BLOCKED"}, headers=headers)
    blocked = login(client, national_code=OTHER_NATIONAL_CODE, password=PASSWORD)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "FORBIDDEN"

    client.patch(status_url(target["id"]), json={"status": "ACTIVE"}, headers=headers)
    assert login(client, national_code=OTHER_NATIONAL_CODE, password=PASSWORD).status_code == 200


def test_cached_profile_shows_the_new_status(client):
    headers, target = staff_and_target(client)
    profile_url = f"{URL}/{target['id']}"
    assert client.get(profile_url, headers=headers).json()["status"] == "ACTIVE"  # now cached

    client.patch(status_url(target["id"]), json={"status": "INACTIVE"}, headers=headers)

    after = client.get(profile_url, headers=headers)
    assert after.headers["X-Cache"] == "MISS"
    assert after.json()["status"] == "INACTIVE"


# ---------- the accounts of the user are NOT changed ----------
@pytest.mark.parametrize("new_status", ["INACTIVE", "BLOCKED"])
def test_status_of_the_accounts_of_the_user_stays_the_same(client, new_status):
    headers, target = staff_and_target(client)
    active_id = create_account(target["id"], "IR740990000000000000000001", "ACTIVE")
    inactive_id = create_account(target["id"], "IR470990000000000000000002", "INACTIVE")

    assert client.patch(status_url(target["id"]), json={"status": new_status}, headers=headers).status_code == 200

    assert client.get(f"/api/v1/accounts/{active_id}").json()["status"] == "ACTIVE"
    assert client.get(f"/api/v1/accounts/{inactive_id}").json()["status"] == "INACTIVE"
    with SessionLocal() as db:
        statuses = {a.id: a.status for a in db.scalars(select(Account).where(Account.user_id == target["id"]))}
    assert statuses == {active_id: "ACTIVE", inactive_id: "INACTIVE"}


def test_accounts_of_other_users_are_untouched(client):
    headers, target = staff_and_target(client)
    admin_account = create_account(stored_user(NATIONAL_CODE).id, "IR740990000000000000000001", "ACTIVE")
    client.patch(status_url(target["id"]), json={"status": "BLOCKED"}, headers=headers)
    assert client.get(f"/api/v1/accounts/{admin_account}").json()["status"] == "ACTIVE"