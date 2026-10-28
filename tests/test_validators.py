from app.validators import is_valid_national_code, is_valid_phone, is_valid_postal_code


def test_national_code_valid():
    for code in ["0013542419", "0499370899", "1234567891"]:
        assert is_valid_national_code(code), code


def test_national_code_invalid():
    bad = [
        "0013542418",  # wrong check digit
        "1111111111",  # all digits equal
        "12345",       # too short
        "00135424190", # too long
        "00135424a9",  # not only digits
        "",
    ]
    for code in bad:
        assert not is_valid_national_code(code), code


def test_phone():
    assert is_valid_phone("09123456789")
    for phone in ["9123456789", "0912345678", "091234567890", "08123456789", "0912345678a"]:
        assert not is_valid_phone(phone), phone


def test_postal_code():
    assert is_valid_postal_code("1593656789")
    for code in ["12345", "159365678", "15936567890", "15936a6789", ""]:
        assert not is_valid_postal_code(code), code
