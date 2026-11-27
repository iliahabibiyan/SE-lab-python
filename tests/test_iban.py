import pytest

from app.iban import BANK_CODE, build_sheba, check_digits, generate_sheba, is_valid_sheba


def test_known_shebas():
    assert build_sheba("0000000000000000001") == "IR740990000000000000000001"
    assert build_sheba("0000000000000000002") == "IR470990000000000000000002"


def test_check_digits_have_two_digits():
    for account_number in ("0000000000000000001", "1234567890123456789", "9999999999999999999"):
        digits = check_digits(BANK_CODE + account_number)
        assert len(digits) == 2 and digits.isdigit()
        assert 2 <= int(digits) <= 98


def test_generated_sheba_is_valid_and_has_the_labbank_bank_code():
    for _ in range(200):
        sheba = generate_sheba()
        assert len(sheba) == 26
        assert sheba.startswith("IR")
        assert sheba[4:7] == "099"  # digits 5 to 7
        assert is_valid_sheba(sheba)


def test_generated_shebas_are_different():
    assert len({generate_sheba() for _ in range(200)}) == 200


def test_any_single_changed_digit_is_detected():
    sheba = build_sheba("0000000000000000001")
    for position in range(2, 26):
        digit = int(sheba[position])
        changed = sheba[:position] + str((digit + 1) % 10) + sheba[position + 1 :]
        assert not is_valid_sheba(changed), position


@pytest.mark.parametrize(
    "sheba",
    [
        "",
        "IR74099000000000000000000",  # 25 characters
        "IR7409900000000000000000011",  # 27 characters
        "GB740990000000000000000001",  # wrong country
        "ir740990000000000000000001",  # lower case
        "IR7409900000000000000000a1",  # a letter
        "IR470990000000000000000001",  # wrong check digits
    ],
)
def test_invalid_shebas(sheba):
    assert not is_valid_sheba(sheba)


@pytest.mark.parametrize("account_number", ["", "123", "00000000000000000001", "000000000000000000a"])
def test_build_sheba_needs_exactly_19_digits(account_number):
    with pytest.raises(ValueError):
        build_sheba(account_number)
