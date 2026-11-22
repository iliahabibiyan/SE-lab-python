"""Demo data with FIXED ids, so that S1 can be tried (and other teams can test against it) without creating data. Enabled with SEED_DATA=1."""

import json
import logging
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Account, User
from app.security import hash_password

logger = logging.getLogger("labbank")

DEMO_PASSWORD = "Str0ng-pass1"

USERS = [
    {
        "id": "0192a7e4-0000-7000-8000-000000000001",
        "national_code": "3740681241",
        "name": "Ali Rezaei",
        "birth_date": date(1995, 3, 21),
        "phone_number": "09123456789",
        "address": "Tehran, Azadi St., No. 10",
        "postal_code": "1593656789",
    },
    {
        "id": "0192a7e4-0000-7000-8000-000000000002",
        "national_code": "6907366258",
        "name": "Sara Ahmadi",
        "birth_date": date(1998, 7, 12),
        "phone_number": "09121234567",
        "address": "Tehran, Valiasr St., No. 20",
        "postal_code": "1946813561",
    },
]

ACCOUNTS = [
    {
        "id": "0192a7e4-6b1d-7c3e-9a41-2f5d8e0b7c11",  # an ACTIVE account
        "user_id": "0192a7e4-0000-7000-8000-000000000001",
        "sheba_number": "IR740990000000000000000001",
        "status": "ACTIVE",
    },
    {
        "id": "0192a7e5-1c2d-7a90-8b33-4d6e9f0a1b22",  # a BLOCKED account
        "user_id": "0192a7e4-0000-7000-8000-000000000002",
        "sheba_number": "IR470990000000000000000002",
        "status": "BLOCKED",
    },
]


def seed_demo_data() -> None:
    """Insert the demo users and accounts that are missing. Safe to run many times."""
    try:
        with SessionLocal() as db:
            for data in USERS:
                if db.get(User, data["id"]) is None:
                    db.add(User(**data, password_hash=hash_password(DEMO_PASSWORD)))
            db.commit()  # the users first: accounts point to them
            for data in ACCOUNTS:
                if db.get(Account, data["id"]) is None:
                    db.add(Account(**data))
            db.commit()
    except IntegrityError as error:  # e.g. somebody already registered one of the demo national codes
        logger.warning(json.dumps({"level": "WARNING", "service": "S1-ACC", "event": "seed_failed", "error": str(error.orig)}))