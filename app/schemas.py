from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.validators import is_valid_national_code, is_valid_phone, is_valid_postal_code


class UserCreate(BaseModel):
    """Request body of POST /api/v1/users (US1)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    national_code: str
    name: str = Field(min_length=1, max_length=100)
    birth_date: date
    phone_number: str
    address: str = Field(min_length=1, max_length=255)
    postal_code: str

    @field_validator("national_code")
    @classmethod
    def check_national_code(cls, v: str) -> str:
        if not is_valid_national_code(v):
            raise ValueError("کد ملی نامعتبر است")
        return v

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, v: str) -> str:
        if not is_valid_phone(v):
            raise ValueError("شماره موبایل نامعتبر است")
        return v

    @field_validator("postal_code")
    @classmethod
    def check_postal_code(cls, v: str) -> str:
        if not is_valid_postal_code(v):
            raise ValueError("کد پستی نامعتبر است")
        return v

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("تاریخ تولد نمی‌تواند در آینده باشد")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    national_code: str
    name: str
    birth_date: date
    status: str
    phone_number: str
    address: str
    postal_code: str
