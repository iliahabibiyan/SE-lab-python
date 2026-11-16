import httpx
import pytest
import respx

from app.clients.s6_client import HttpS6Client, S6Unavailable

BASE = "http://s6.test"
ACCOUNT_ID = "0192a7e4-6b1d-7c3e-9a41-2f5d8e0b7c11"
URL = f"{BASE}/api/v1/accounts/{ACCOUNT_ID}/exceptions"
ITEMS = [{"id": "exc-1", "type": "MISSING_LEDGER_ENTRY"}]


@respx.mock
def test_returns_the_exceptions_of_s6():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"items": ITEMS, "next_cursor": None}))
    assert HttpS6Client(BASE).get_exceptions(ACCOUNT_ID, "corr-1") == ITEMS
    assert route.calls.last.request.headers["X-Correlation-ID"] == "corr-1"


@respx.mock
def test_unknown_account_means_no_exceptions():
    respx.get(URL).mock(return_value=httpx.Response(404, json={"code": "NOT_FOUND"}))
    assert HttpS6Client(BASE).get_exceptions(ACCOUNT_ID) == []


@respx.mock
def test_server_error_is_reported_as_unavailable():
    respx.get(URL).mock(return_value=httpx.Response(503, json={"code": "SERVICE_UNAVAILABLE"}))
    with pytest.raises(S6Unavailable):
        HttpS6Client(BASE).get_exceptions(ACCOUNT_ID)


@respx.mock
def test_timeout_is_reported_as_unavailable():
    respx.get(URL).mock(side_effect=httpx.ReadTimeout("too slow"))
    with pytest.raises(S6Unavailable):
        HttpS6Client(BASE).get_exceptions(ACCOUNT_ID)


@respx.mock
def test_connection_error_is_reported_as_unavailable():
    respx.get(URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(S6Unavailable):
        HttpS6Client(BASE).get_exceptions(ACCOUNT_ID)


@respx.mock
def test_answer_with_an_unexpected_shape_is_reported_as_unavailable():
    respx.get(URL).mock(return_value=httpx.Response(200, text="<html>not json</html>"))
    with pytest.raises(S6Unavailable):
        HttpS6Client(BASE).get_exceptions(ACCOUNT_ID)
    respx.get(URL).mock(return_value=httpx.Response(200, json={"unexpected": []}))
    with pytest.raises(S6Unavailable):
        HttpS6Client(BASE).get_exceptions(ACCOUNT_ID)


def test_missing_base_url_is_reported_as_unavailable():
    with pytest.raises(S6Unavailable):
        HttpS6Client(None).get_exceptions(ACCOUNT_ID)