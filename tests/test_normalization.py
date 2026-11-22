from app.validators import is_valid_postal_code, normalize_digits, normalize_phone, normalize_text
from tests.helpers import to_arabic_digits, to_persian_digits, valid_payload

URL = "/api/v1/users"


def test_normalize_digits():
    assert normalize_digits(to_persian_digits("0013542419")) == "0013542419"
    assert normalize_digits(to_arabic_digits("0013542419")) == "0013542419"


def test_normalize_phone():
    for raw in ["09123456789", "+989123456789", "00989123456789", "989123456789", "9123456789", to_persian_digits("09123456789")]:
        assert normalize_phone(raw) == "09123456789", raw


def test_normalize_text():
    assert normalize_text("  Ali   Rezaei ") == "Ali Rezaei"  # extra spaces are collapsed
    assert normalize_text("\u064a \u0643") == "\u06cc \u06a9"  # Arabic yeh and kaf become Persian yeh and kaf


def test_postal_code_rules():
    assert is_valid_postal_code("1593656789")
    assert not is_valid_postal_code("0593656789")  # starts with 0
    assert not is_valid_postal_code("2593656789")  # contains 2 in the first five digits
    assert not is_valid_postal_code("1111656789")  # four equal digits at the start
    assert not is_valid_postal_code("1593556789")  # 5th digit can not be 5


def test_register_with_persian_digits_and_extra_spaces(client):
    payload = valid_payload(
        national_code=to_persian_digits("0013542419"),
        phone_number="+98 912 345 6789",
        postal_code=to_persian_digits("1593656789"),
        name="  Ali   Rezaei ",
    )
    response = client.post(URL, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["national_code"] == "0013542419"
    assert body["phone_number"] == "09123456789"
    assert body["postal_code"] == "1593656789"
    assert body["name"] == "Ali Rezaei"


def test_register_rejects_invalid_postal_prefix(client):
    response = client.post(URL, json=valid_payload(postal_code="2593656789"))
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "postal_code"


def test_duplicate_detected_after_normalization(client):
    assert client.post(URL, json=valid_payload()).status_code == 201
    response = client.post(URL, json=valid_payload(national_code=to_persian_digits("0013542419")))
    assert response.status_code == 409
