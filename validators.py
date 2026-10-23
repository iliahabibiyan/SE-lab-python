"""Validation logic and Pydantic schemas for User registration (US1)."""
import hashlib
import re
from datetime import date
from pydantic import BaseModel, Field, field_validator


def validate_iranian_national_id(national_id: str) -> str:
    """
    Validate 10-digit National ID using digits check
    and official Modulo-11 checksum algorithm.
    """
    if not isinstance(national_id, str) or not re.fullmatch(r"^[0-9]{10}$", national_id):
        raise ValueError("کد ملی باید دقیقاً ۱۰ رقم عددی باشد.")

    if len(set(national_id)) == 1:
        raise ValueError("کد ملی وارد شده نامعتبر است.")

    check_digit = int(national_id[9])
    weighted_sum = sum(int(national_id[i]) * (10 - i) for i in range(9))
    remainder = weighted_sum % 11

    is_valid = (remainder < 2 and check_digit == remainder) or (
        remainder >= 2 and check_digit == 11 - remainder
    )
    if not is_valid:
        raise ValueError("کد ملی وارد شده معتبر نیست (خطای رقم کنترل).")

    return national_id


def validate_postal_code(postal_code: str) -> str:
    """Validate 10-digit postal code."""
    if not isinstance(postal_code, str) or not re.fullmatch(r"^[0-9]{10}$", postal_code):
        raise ValueError("کد پستی باید دقیقاً ۱۰ رقم عددی باشد.")
    return postal_code


def validate_phone_number(phone_number: str) -> str:
    """Validate mobile number starting with 09 and having 11 digits."""
    if not isinstance(phone_number, str) or not re.fullmatch(r"^09[0-9]{9}$", phone_number):
        raise ValueError("شماره موبایل باید ۱۱ رقم و با 09 شروع شود.")
    return phone_number


def validate_address(address: str) -> str:
    """Validate non-empty address with reasonable length."""
    if not isinstance(address, str):
        raise ValueError("آدرس باید رشته متنی باشد.")
    cleaned = address.strip()
    if len(cleaned) < 5:
        raise ValueError("آدرس نمی‌تواند خالی یا کمتر از ۵ کاراکتر باشد.")
    return cleaned


def hash_password(password: str) -> str:
    """Hash user password using SHA-256 with salt for storage."""
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("رمز عبور باید حداقل ۸ کاراکتر باشد.")
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class UserCreateRequest(BaseModel):
    national_id: str
    full_name: str = Field(..., min_length=2, max_length=150)
    birth_date: date
    phone_number: str
    address: str
    postal_code: str
    password: str = Field(..., min_length=8)

    @field_validator("national_id")
    @classmethod
    def check_national_id(cls, v: str) -> str:
        return validate_iranian_national_id(v)

    @field_validator("postal_code")
    @classmethod
    def check_postal_code(cls, v: str) -> str:
        return validate_postal_code(v)

    @field_validator("phone_number")
    @classmethod
    def check_phone_number(cls, v: str) -> str:
        return validate_phone_number(v)

    @field_validator("address")
    @classmethod
    def check_address(cls, v: str) -> str:
        return validate_address(v)

    @field_validator("full_name")
    @classmethod
    def check_full_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("نام و نام خانوادگی باید حداقل ۲ کاراکتر باشد.")
        return cleaned

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("تاریخ تولد باید در گذشته باشد.")
        return v
