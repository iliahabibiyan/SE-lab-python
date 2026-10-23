"""Pure input validators for ACC1-S (standard library only).

Kept free of Pydantic/FastAPI so they are easy to unit-test and reuse
(e.g. from a future event consumer or CLI).
"""
import re

# Persian (U+06F0..) and Arabic-Indic (U+0660..) digits -> ASCII digits.
_DIGITS_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

_NATIONAL_CODE_RE = re.compile(r"[0-9]{10}")
# Iranian postal code rules:
#   - first 4 digits are not all the same
#   - first 4 digits contain no 0 or 2
#   - 5th digit is not 0, 2 or 5
#   - remaining 5 digits contain no 2
_POSTAL_CODE_RE = re.compile(r"(?!([0-9])\1{3})[13-9]{4}[1346-9][013-9]{5}")
_PHONE_RE = re.compile(r"09[0-9]{9}")


def normalize_digits(value: str) -> str:
    """Strip whitespace and convert Persian/Arabic digits to ASCII."""
    return value.translate(_DIGITS_MAP).strip()


def national_code_check_digit(first_nine: str) -> int:
    """Expected 10th digit for the first nine digits of a national code."""
    total = sum(int(d) * w for d, w in zip(first_nine, range(10, 1, -1)))
    remainder = total % 11
    return remainder if remainder < 2 else 11 - remainder


def is_valid_national_code(code: str) -> bool:
    """Validate an Iranian national code (expects ASCII digits)."""
    if not isinstance(code, str) or not _NATIONAL_CODE_RE.fullmatch(code):
        return False
    if len(set(code)) == 1:  # 0000000000, 1111111111, ... pass the checksum
        return False
    return int(code[9]) == national_code_check_digit(code[:9])


def mask_national_code(code: str) -> str:
    """Safe form for logs (GEN-11 forbids logging the full national code)."""
    if len(code) < 6:
        return "*" * len(code)
    return code[:3] + "*" * (len(code) - 5) + code[-2:]


def is_valid_postal_code(code: str) -> bool:
    """Validate an Iranian 10-digit postal code (expects ASCII digits)."""
    return isinstance(code, str) and _POSTAL_CODE_RE.fullmatch(code) is not None


def normalize_phone(value: str) -> str:
    """Normalize a mobile number to the local 09xxxxxxxxx form.

    Accepts Persian digits, spaces/dashes and the +98 / 0098 / 98 prefixes.
    """
    v = re.sub(r"[\s\-]", "", normalize_digits(value))
    for prefix in ("+98", "0098", "98"):
        if v.startswith(prefix) and len(v) == len(prefix) + 10:
            return "0" + v[len(prefix):]
    return v


def is_valid_phone(phone: str) -> bool:
    """Validate a normalized Iranian mobile number (09xxxxxxxxx)."""
    return isinstance(phone, str) and _PHONE_RE.fullmatch(phone) is not None
