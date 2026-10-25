import uuid

from tests.helpers import valid_payload

URL = "/api/v1/users"


def test_register_success(client):
    response = client.post(URL, json=valid_payload())
    assert response.status_code == 201
    body = response.json()
    uuid.UUID(body["id"])  # id is a valid UUID
    assert body["status"] == "ACTIVE"
    assert body["national_code"] == "0013542419"
    assert body["name"] == "علی رضایی"
    assert body["birth_date"] == "1995-03-21"
    assert body["phone_number"] == "09123456789"
    assert body["postal_code"] == "1593656789"
    assert "X-Correlation-ID" in response.headers


def test_register_duplicate_national_code(client):
    assert client.post(URL, json=valid_payload()).status_code == 201
    response = client.post(URL, json=valid_payload(name="کس دیگر"))
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "CONFLICT"
    assert body["detail"] == "کد ملی تکراری است"


def test_register_missing_fields(client):
    response = client.post(URL, json={"national_code": "0013542419"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    fields = {e["field"] for e in body["errors"]}
    assert {"name", "birth_date", "phone_number", "address", "postal_code"} <= fields


def test_register_invalid_values(client):
    cases = {
        "national_code": "0013542418",
        "phone_number": "12345",
        "postal_code": "12345",
        "birth_date": "2999-01-01",
        "name": "",
        "address": "",
    }
    for field, value in cases.items():
        response = client.post(URL, json=valid_payload(**{field: value}))
        assert response.status_code == 400, field
        assert response.json()["errors"][0]["field"] == field


def test_register_cannot_set_status(client):
    response = client.post(URL, json=valid_payload(status="BLOCKED"))
    assert response.status_code == 400


def test_correlation_id_is_echoed(client):
    response = client.post(URL, json=valid_payload(), headers={"X-Correlation-ID": "abc-123"})
    assert response.headers["X-Correlation-ID"] == "abc-123"
