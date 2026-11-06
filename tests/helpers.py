from sqlalchemy import select

from app.database import SessionLocal
from app.models import User

PASSWORD = "Str0ng-pass1"
NATIONAL_CODE = "0013542419"
OTHER_NATIONAL_CODE = "0499370899"


def valid_payload(**overrides) -> dict:
    payload = {
        "national_code": NATIONAL_CODE,
        "name": "علی رضایی",
        "birth_date": "1995-03-21",
        "phone_number": "09123456789",
        "address": "تهران، خیابان آزادی، پلاک ۱۰",
        "postal_code": "1593656789",
        "password": PASSWORD,
    }
    payload.update(overrides)
    return payload


def register_user(client, **overrides) -> dict:
    response = client.post("/api/v1/users", json=valid_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def login(client, national_code=NATIONAL_CODE, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"national_code": national_code, "password": password})


def register_and_login(client) -> dict:
    """Register the default user, log in and return the login response body."""
    register_user(client)
    response = login(client)
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def update_user(national_code: str, **fields) -> None:
    """Change columns of a user directly in the database (e.g. status)."""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.national_code == national_code))
        for name, value in fields.items():
            setattr(user, name, value)
        db.commit()


def register_other_user(client) -> dict:
    """A second user (a normal user, same password)."""
    return register_user(client, national_code=OTHER_NATIONAL_CODE, phone_number="09121234567")


def token_for(client, national_code=NATIONAL_CODE) -> str:
    response = login(client, national_code=national_code)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def make_admin(national_code=NATIONAL_CODE) -> None:
    update_user(national_code, role="ADMIN")