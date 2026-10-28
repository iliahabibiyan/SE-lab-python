from app.validators import is_valid_postal_code, normalize_digits, normalize_phone, normalize_text
from tests.helpers import valid_payload

URL = "/api/v1/users"


def test_normalize_digits():
    assert normalize_digits("۰۰۱۳۵۴۲۴۱۹") == "0013542419"
    assert normalize_digits("٠٠١٣٥٤٢٤١٩") == "0013542419"


def test_normalize_phone():
    for raw in ["09123456789", "+989123456789", "00989123456789", "989123456789", "9123456789", "۰۹۱۲۳۴۵۶۷۸۹"]:
        assert normalize_phone(raw) == "09123456789", raw


def test_normalize_text():
    assert normalize_text("  علي   رضايي ") == "علی رضایی"


def test_postal_code_rules():
    assert is_valid_postal_code("1593656789")
    assert not is_valid_postal_code("0593656789")  # starts with 0
    assert not is_valid_postal_code("2593656789")  # contains 2 in the first five digits
    assert not is_valid_postal_code("1111656789")  # four equal digits at the start
    assert not is_valid_postal_code("1593556789")  # 5th digit can not be 5


def test_register_with_persian_digits_and_extra_spaces(client):
    payload = valid_payload(
        national_code="۰۰۱۳۵۴۲۴۱۹",
        phone_number="+98 912 345 6789",
        postal_code="۱۵۹۳۶۵۶۷۸۹",
        name="  علي   رضايي ",
    )
    response = client.post(URL, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["national_code"] == "0013542419"
    assert body["phone_number"] == "09123456789"
    assert body["postal_code"] == "1593656789"
    assert body["name"] == "علی رضایی"


def test_register_rejects_invalid_postal_prefix(client):
    response = client.post(URL, json=valid_payload(postal_code="2593656789"))
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "postal_code"


def test_duplicate_detected_after_normalization(client):
    assert client.post(URL, json=valid_payload()).status_code == 201
    response = client.post(URL, json=valid_payload(national_code="۰۰۱۳۵۴۲۴۱۹"))
    assert response.status_code == 409
