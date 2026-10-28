import re


def is_valid_national_code(value: str) -> bool:
    """Iranian national code: 10 digits + check digit (mod 11 algorithm)."""
    if not re.fullmatch(r"\d{10}", value) or len(set(value)) == 1:
        return False
    total = sum(int(value[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    check = remainder if remainder < 2 else 11 - remainder
    return check == int(value[9])


def is_valid_phone(value: str) -> bool:
    """Iranian mobile number, e.g. 09123456789."""
    return re.fullmatch(r"09\d{9}", value) is not None


def is_valid_postal_code(value: str) -> bool:
    """Iranian postal code: exactly 10 digits."""
    return re.fullmatch(r"\d{10}", value) is not None
