"""Iranian Sheba numbers (IBAN, ISO 13616): IR + 2 check digits + 3 digit bank code + 19 digit account number."""

import re
import secrets

BANK_CODE = "099"  # LabBank (GEN-13); every other bank code belongs to an external bank
ACCOUNT_NUMBER_DIGITS = 19


def check_digits(bban: str) -> str:
    """The 2 check digits of a 22 digit BBAN: 98 - (BBAN + "IR00" with letters as numbers) mod 97 (I=18, R=27)."""
    return f"{98 - int(bban + '182700') % 97:02d}"


def build_sheba(account_number: str) -> str:
    """Sheba of a LabBank account with the given 19 digit account number."""
    if not re.fullmatch(rf"\d{{{ACCOUNT_NUMBER_DIGITS}}}", account_number):
        raise ValueError("account number must have exactly 19 digits")
    bban = BANK_CODE + account_number
    return f"IR{check_digits(bban)}{bban}"


def is_valid_sheba(sheba: str) -> bool:
    """Format (IR + 24 digits) and the mod 97 check of ISO 13616."""
    if not re.fullmatch(r"IR\d{24}", sheba):
        return False
    return int(sheba[4:] + "1827" + sheba[2:4]) % 97 == 1


def generate_sheba() -> str:
    """A new Sheba with a random account number (the database refuses a duplicate; the caller retries)."""
    account_number = f"{secrets.randbelow(10**ACCOUNT_NUMBER_DIGITS):0{ACCOUNT_NUMBER_DIGITS}d}"
    return build_sheba(account_number)
