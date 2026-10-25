"""DTOs (request/response models) for the `users` resource.

Request DTOs validate and normalize input; the response DTO is deliberately
lenient so legacy rows can never make a GET fail.
"""
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from validators import (
    is_valid_national_code,
    is_valid_phone,
    is_valid_postal_code,
    normalize_digits,
    normalize_phone,
)

TEHRAN = ZoneInfo("Asia/Tehran")  # GEN-05: "day" calculations use Tehran time
MIN_BIRTH_DATE = date(1900, 1, 1)
NAME_MAX_LENGTH = 150  # matches the DB column
ADDRESS_MAX_LENGTH = 500  # API-level cap (assumption, DB column is TEXT)


class UserStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DISABLED = "disabled"


def today_tehran() -> date:
    return datetime.now(TEHRAN).date()


def _digits(value):
    return normalize_digits(value) if isinstance(value, str) else value


def _phone(value):
    return normalize_phone(value) if isinstance(value, str) else value


def _check_national_code(value: str) -> str:
    if not is_valid_national_code(value):
        raise ValueError("national code is not valid")
    return value


def _check_postal_code(value: str) -> str:
    if not is_valid_postal_code(value):
        raise ValueError("postal code is not valid")
    return value


def _check_phone(value: str) -> str:
    if not is_valid_phone(value):
        raise ValueError("phone must be an Iranian mobile number like 09123456789")
    return value


NationalCode = Annotated[
    str,
    BeforeValidator(_digits),
    AfterValidator(_check_national_code),
    Field(description="10-digit Iranian national code (checksum verified)"),
]
PostalCode = Annotated[
    str,
    BeforeValidator(_digits),
    AfterValidator(_check_postal_code),
    Field(description="10-digit Iranian postal code"),
]
Phone = Annotated[
    str,
    BeforeValidator(_phone),
    AfterValidator(_check_phone),
    Field(description="Iranian mobile number, e.g. 09123456789"),
]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH)
]
Address = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=ADDRESS_MAX_LENGTH),
]


def _check_birth_date(value: date) -> date:
    if value < MIN_BIRTH_DATE:
        raise ValueError(f"birth_date must be on or after {MIN_BIRTH_DATE.isoformat()}")
    if value > today_tehran():
        raise ValueError("birth_date cannot be in the future")
    return value


BirthDate = Annotated[date, AfterValidator(_check_birth_date)]


class _RequestModel(BaseModel):
    # Unknown fields are rejected. hide_input_in_errors keeps inputs (e.g. the
    # national code) out of str(exc) and logs (GEN-11); the HTTP error handler
    # must also drop "input" from exc.errors() before building the response.
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class UserCreate(_RequestModel):
    """Body of POST /api/v1/users. `id` and `status` are set by the server."""

    national_code: NationalCode
    name: Name
    birth_date: BirthDate
    phone: Phone
    address: Address
    postal_code: PostalCode


class UserUpdate(_RequestModel):
    """Body of PATCH /api/v1/users/{id}. National code and birth date are immutable."""

    name: Name | None = None
    phone: Phone | None = None
    address: Address | None = None
    postal_code: PostalCode | None = None
    status: UserStatus | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("provided fields cannot be null")
        return self


class UserResponse(BaseModel):
    """Representation returned by the API (the 8 fields of the `users` table)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    national_code: str
    name: str
    birth_date: date
    status: UserStatus
    phone: str
    address: str
    postal_code: str
