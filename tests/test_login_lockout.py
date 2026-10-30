from datetime import timedelta

from app.routers.auth import MAX_FAILED_ATTEMPTS
from app.utils import utcnow
from tests.helpers import NATIONAL_CODE, login, register_user, update_user


def fail_login(client, times: int) -> list[int]:
    return [login(client, password="wrong-password").status_code for _ in range(times)]


def test_account_is_locked_after_5_wrong_passwords(client):
    register_user(client)
    assert MAX_FAILED_ATTEMPTS == 5
    assert fail_login(client, 5) == [401] * 5

    response = login(client)  # even the correct password is refused while locked
    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "LOGIN_TEMPORARILY_LOCKED"
    assert body["retry_after_seconds"] > 0
    assert int(response.headers["Retry-After"]) == body["retry_after_seconds"]
    assert response.headers["content-type"].startswith("application/problem+json")


def test_successful_login_resets_the_counter(client):
    register_user(client)
    assert fail_login(client, 4) == [401] * 4
    assert login(client).status_code == 200
    assert fail_login(client, 4) == [401] * 4  # counting started again from zero
    assert login(client).status_code == 200


def test_lock_expires(client):
    register_user(client)
    fail_login(client, 5)
    assert login(client).status_code == 429
    update_user(NATIONAL_CODE, locked_until=utcnow() - timedelta(minutes=1))  # simulate 15 minutes later
    assert login(client).status_code == 200


def test_unknown_national_code_is_never_locked(client):
    statuses = {login(client, national_code="0499370899").status_code for _ in range(7)}
    assert statuses == {401}


def test_other_users_are_not_affected(client):
    register_user(client)
    register_user(client, national_code="0499370899", phone_number="09121234567")
    fail_login(client, 5)
    assert login(client).status_code == 429
    assert login(client, national_code="0499370899").status_code == 200