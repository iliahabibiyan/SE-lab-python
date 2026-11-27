import pytest

from app.clients.s2_client import get_s2_client
from main import app
from tests.fake_s2 import FakeS2Client
from tests.helpers import auth_header, register_user, token_for

URL = "/api/v1/accounts"


@pytest.fixture
def fake_s2():
    fake = FakeS2Client()
    app.dependency_overrides[get_s2_client] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def open_account(client, headers=None):
    me = register_user(client)
    all_headers = {**auth_header(token_for(client)), **(headers or {})}
    return client.post(URL, json={"user_id": me["id"]}, headers=all_headers)


def test_s2_is_told_about_the_new_account(client, fake_s2):
    response = open_account(client, {"X-Correlation-ID": "corr-9"})
    assert response.status_code == 201
    assert fake_s2.calls == [(response.json()["id"], "corr-9")]  # same id, same correlation id


def test_the_account_is_created_even_when_s2_is_down(client, fake_s2):
    fake_s2.down = True
    response = open_account(client)
    assert response.status_code == 201  # no 500: S2 is not vital for opening an account
    assert response.json()["status"] == "ACTIVE"
    assert len(fake_s2.calls) == 1


def test_s2_is_not_told_when_the_account_is_refused(client, fake_s2):
    register_user(client)
    other_headers = auth_header(token_for(client))
    response = client.post(URL, json={"user_id": "00000000-0000-7000-8000-000000000000"}, headers=other_headers)
    assert response.status_code == 403
    assert fake_s2.calls == []