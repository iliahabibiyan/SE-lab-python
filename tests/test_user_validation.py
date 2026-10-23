"""Unit tests for Task 1.4: National ID, Postal Code, Phone, and User Registration Validation."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from validators import (
    UserCreateRequest,
    validate_address,
    validate_iranian_national_id,
    validate_phone_number,
    validate_postal_code,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Unit Tests for National ID 
# ---------------------------------------------------------------------------
def test_valid_national_id():
    assert validate_iranian_national_id("0013542419") == "0013542419"
    assert validate_iranian_national_id("0499370899") == "0499370899"


@pytest.mark.parametrize(
    "invalid_nid",
    [
        "123456789",      # 9 digits (too short)
        "12345678901",    # 11 digits (too long)
        "001354241A",     # contains non-digit character
        "1111111111",     # all identical digits
        "0000000000",     # all zeros
        "0013542418",     # invalid checksum digit
        "",               # empty
    ],
)
def test_invalid_national_id_raises_value_error(invalid_nid: str):
    with pytest.raises(ValueError):
        validate_iranian_national_id(invalid_nid)


# ---------------------------------------------------------------------------
# 2. Unit Tests for Postal Code
# ---------------------------------------------------------------------------
def test_valid_postal_code():
    assert validate_postal_code("1415563111") == "1415563111"


@pytest.mark.parametrize(
    "invalid_postal",
    [
        "14155",          # less than 10 digits
        "14155631112",    # more than 10 digits
        "141556311A",     # contains letters
        "14155-6311",     # contains dash
        "",               # empty
    ],
)
def test_invalid_postal_code_raises_value_error(invalid_postal: str):
    with pytest.raises(ValueError):
        validate_postal_code(invalid_postal)


# ---------------------------------------------------------------------------
# 3. Unit Tests for Phone Number & Address
# ---------------------------------------------------------------------------
def test_valid_phone_number():
    assert validate_phone_number("09123456789") == "09123456789"


@pytest.mark.parametrize(
    "invalid_phone",
    [
        "9123456789",     # missing leading 0
        "08123456789",    # does not start with 09
        "0912345678",     # 10 digits
        "091234567890",   # 12 digits
        "0912345678a",    # non-numeric
    ],
)
def test_invalid_phone_number(invalid_phone: str):
    with pytest.raises(ValueError):
        validate_phone_number(invalid_phone)


def test_address_validation():
    assert validate_address("  تهران، خیابان آزادی، پلاک ۱۰  ") == "تهران، خیابان آزادی، پلاک ۱۰"
    with pytest.raises(ValueError):
        validate_address("   ")
    with pytest.raises(ValueError):
        validate_address("تست")
    with pytest.raises(ValueError):
        validate_address("123")


# ---------------------------------------------------------------------------
# 4. Schema & Endpoint Tests (Given / When / Then for US1)
# ---------------------------------------------------------------------------
def test_user_create_schema_future_birth_date():
    future_date = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        UserCreateRequest(
            national_id="0013542419",
            full_name="ایلیا حبیبیان",
            birth_date=future_date,
            phone_number="09123456789",
            address="تهران، خیابان ولیعصر، کوچه اول",
            postal_code="1415563111",
            password="SecurePassword123",
        )


@patch("main.get_conn")
def test_register_user_endpoint_success_201(mock_get_conn):
    fake_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (
        fake_id,
        "0013542419",
        "ایلیا حبیبیان",
        date(2002, 5, 15),
        "active",
        "09123456789",
        "تهران، خیابان ولیعصر، پلاک ۱۰",
        "1415563111",
        now,
        now,
    )
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    response = client.post(
        "/api/v1/users",
        json={
            "national_id": "0013542419",
            "full_name": "ایلیا حبیبیان",
            "birth_date": "2002-05-15",
            "phone_number": "09123456789",
            "address": "تهران، خیابان ولیعصر، پلاک ۱۰",
            "postal_code": "1415563111",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(fake_id)
    assert data["national_id"] == "0013542419"
    assert data["status"] == "active"


@patch("main.get_conn")
def test_register_user_duplicate_national_id_returns_409(mock_get_conn):
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = psycopg.errors.UniqueViolation("Duplicate key")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    response = client.post(
        "/api/v1/users",
        json={
            "national_id": "0013542419",
            "full_name": "ایلیا حبیبیان",
            "birth_date": "2002-05-15",
            "phone_number": "09123456789",
            "address": "تهران، خیابان ولیعصر، پلاک ۱۰",
            "postal_code": "1415563111",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 409


def test_register_user_invalid_payload_returns_422():
    response = client.post(
        "/api/v1/users",
        json={
            "national_id": "123",  # Invalid
            "full_name": "ایلیا حبیبیان",
            "birth_date": "2002-05-15",
            "phone_number": "09123456789",
            "address": "تهران، خیابان ولیعصر",
            "postal_code": "14155",  # Invalid
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 422
