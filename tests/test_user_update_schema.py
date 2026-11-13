import pytest
from pydantic import ValidationError

from app.schemas import UserUpdate

VALID = {
    "phone_number": "09129998877",
    "address": "تهران، خیابان انقلاب، پلاک ۵",
    "postal_code": "1946813561",
}


def test_valid_update():
    update = UserUpdate(**VALID)
    assert update.phone_number == "09129998877"
    assert update.postal_code == "1946813561"


def test_values_are_normalized():
    update = UserUpdate(
        phone_number="+98 912 999 8877",
        address="  تهران،   خیابان انقلاب   ",
        postal_code="۱۹۴۶۸۱۳۵۶۱",
    )
    assert update.phone_number == "09129998877"
    assert update.address == "تهران، خیابان انقلاب"
    assert update.postal_code == "1946813561"


@pytest.mark.parametrize(
    "field, value",
    [
        ("phone_number", "123"),
        ("phone_number", "08129998877"),
        ("phone_number", "0912999887a"),
        ("postal_code", "12345"),
        ("postal_code", "19468135611"),
        ("postal_code", "2946813561"),  # official rule: no 0 or 2 in the first digits
        ("address", ""),
        ("address", "     "),
        ("address", "abc"),
    ],
)
def test_invalid_values_are_rejected(field, value):
    with pytest.raises(ValidationError) as error:
        UserUpdate(**{**VALID, field: value})
    assert error.value.errors()[0]["loc"] == (field,)


def test_all_three_fields_are_required():
    with pytest.raises(ValidationError) as error:
        UserUpdate()
    assert {e["loc"][0] for e in error.value.errors()} == {"phone_number", "address", "postal_code"}


def test_other_fields_are_rejected():
    for extra in ({"national_code": "0013542419"}, {"role": "ADMIN"}, {"status": "BLOCKED"}, {"name": "x"}):
        with pytest.raises(ValidationError):
            UserUpdate(**VALID, **extra)