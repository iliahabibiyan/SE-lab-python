import re

# Persian (۰-۹) and Arabic-Indic (٠-٩) digits -> English digits
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
# Arabic letters that are often typed by mistake -> Persian letters
_LETTERS = str.maketrans("يك", "یک")

# Iranian postal code: first 4 digits from [1,3-9] (not all equal), 5th from [1,3,4,6-9], last 5 from [0,1,3-9]
_POSTAL_PATTERN = re.compile(r"(?!(\d)\1{3})[13-9]{4}[1346-9][013-9]{5}")


def normalize_digits(value: str) -> str:
    return value.translate(_DIGITS).strip()


def normalize_text(value: str) -> str:
    """Fix Arabic letters and collapse repeated whitespace."""
    return " ".join(value.translate(_LETTERS).split())


def normalize_phone(value: str) -> str:
    """+98912..., 0098912..., 98912..., 912... -> 0912..."""
    phone = normalize_digits(value).replace(" ", "").replace("-", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("0098"):
        phone = "0" + phone[4:]
    elif phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    elif phone.startswith("9") and len(phone) == 10:
        phone = "0" + phone
    return phone


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
    """Iranian postal code with the official digit rules."""
    return _POSTAL_PATTERN.fullmatch(value) is not None
