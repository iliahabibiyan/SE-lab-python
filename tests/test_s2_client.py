import json

import httpx
import pytest
import respx

from app.clients.s2_client import HttpS2Client, S2Unavailable

BASE = "http://s2.test"
URL = f"{BASE}/api/v1/accounts"
ACCOUNT_ID = "0192a7e4-6b1d-7c3e-9a41-2f5d8e0b7c11"


@respx.mock
def test_account_created_is_sent_as_the_contract_says():
    route = respx.post(URL).mock(return_value=httpx.Response(204))
    HttpS2Client(BASE).account_created(ACCOUNT_ID, "corr-1")
    request = route.calls.last.request
    assert json.loads(request.content) == {"account_id": ACCOUNT_ID}
    assert request.headers["Idempotency-Key"] == ACCOUNT_ID
    assert request.headers["X-Correlation-ID"] == "corr-1"


@respx.mock
@pytest.mark.parametrize("status", [200, 201, 204])
def test_success_codes(status):
    respx.post(URL).mock(return_value=httpx.Response(status))
    HttpS2Client(BASE).account_created(ACCOUNT_ID)


@respx.mock
@pytest.mark.parametrize("status", [400, 409, 500, 503])
def test_error_answers_are_reported_as_unavailable(status):
    respx.post(URL).mock(return_value=httpx.Response(status, json={"code": "X"}))
    with pytest.raises(S2Unavailable):
        HttpS2Client(BASE).account_created(ACCOUNT_ID)


@respx.mock
def test_timeout_and_connection_errors_are_reported_as_unavailable():
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("too slow"))
    with pytest.raises(S2Unavailable):
        HttpS2Client(BASE).account_created(ACCOUNT_ID)
    respx.post(URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(S2Unavailable):
        HttpS2Client(BASE).account_created(ACCOUNT_ID)


def test_missing_base_url_is_reported_as_unavailable():
    with pytest.raises(S2Unavailable):
        HttpS2Client(None).account_created(ACCOUNT_ID)


@respx.mock
def test_any_unexpected_client_error_is_reported_as_unavailable():
    respx.post(URL).mock(side_effect=RuntimeError("boom"))
    with pytest.raises(S2Unavailable):
        HttpS2Client(BASE).account_created(ACCOUNT_ID)
