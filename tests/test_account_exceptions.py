import pytest

from app.clients.s6_client import get_s6_client
from main import app
from tests.fakes import FakeS6Client
from tests.helpers import register_user
from tests.test_get_account import create_account

URL = "/api/v1/accounts"
ITEMS = [{"id": "exc-1", "type": "MISSING_LEDGER_ENTRY"}]


@pytest.fixture
def fake_s6():
    fake = FakeS6Client(ITEMS)
    app.dependency_overrides[get_s6_client] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def new_account(client) -> str:
    return create_account(register_user(client)["id"])


def test_account_is_returned_without_exceptions_by_default(client, fake_s6):
    account_id = new_account(client)
    body = client.get(f"{URL}/{account_id}").json()
    assert "exceptions" not in body
    assert "exceptions_available" not in body
    assert fake_s6.calls == []  # S6 is not asked


def test_account_with_exceptions_from_s6(client, fake_s6):
    account_id = new_account(client)
    response = client.get(f"{URL}/{account_id}", params={"include": "exceptions"}, headers={"X-Correlation-ID": "corr-7"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == account_id
    assert body["exceptions"] == ITEMS
    assert body["exceptions_available"] is True
    assert fake_s6.calls == [(account_id, "corr-7")]  # the correlation id is passed on


def test_account_is_still_returned_when_s6_is_down(client, fake_s6):
    fake_s6.down = True
    account_id = new_account(client)
    response = client.get(f"{URL}/{account_id}", params={"include": "exceptions"})
    assert response.status_code == 200  # no 500
    body = response.json()
    assert body["id"] == account_id
    assert body["status"] == "ACTIVE"
    assert body["exceptions_available"] is False
    assert "exceptions" not in body


def test_unknown_account_does_not_call_s6(client, fake_s6):
    response = client.get(f"{URL}/00000000-0000-7000-8000-000000000000", params={"include": "exceptions"})
    assert response.status_code == 404
    assert fake_s6.calls == []


def test_unsupported_include_value(client, fake_s6):
    account_id = new_account(client)
    response = client.get(f"{URL}/{account_id}", params={"include": "everything"})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "include"