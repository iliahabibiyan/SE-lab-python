from app.database import SessionLocal
from app.models import Account
from app.seed import ACCOUNTS, seed_demo_data
from tests.helpers import register_user

URL = "/api/v1/accounts"
SHEBA = "IR740990000000000000000001"


def create_account(user_id: str, status: str = "ACTIVE", sheba: str = SHEBA) -> str:
    """Insert an account straight into the database and return its id."""
    with SessionLocal() as db:
        account = Account(user_id=user_id, sheba_number=sheba, status=status)
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.id


def test_get_account_success(client):
    user = register_user(client)
    account_id = create_account(user["id"])
    response = client.get(f"{URL}/{account_id}")  # no token: service to service call
    assert response.status_code == 200
    assert response.json() == {
        "id": account_id,
        "user_id": user["id"],
        "sheba_number": SHEBA,
        "status": "ACTIVE",
        "account_type": "CURRENT",
    }


def test_get_account_shows_the_status(client):
    user = register_user(client)
    account_id = create_account(user["id"], status="BLOCKED")
    assert client.get(f"{URL}/{account_id}").json()["status"] == "BLOCKED"


def test_get_account_not_found(client):
    response = client.get(f"{URL}/00000000-0000-7000-8000-000000000000")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "NOT_FOUND"


def test_get_account_with_invalid_id(client):
    response = client.get(f"{URL}/not-a-uuid")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "account_id"


def test_seed_creates_the_demo_accounts_and_can_run_twice(client):
    seed_demo_data()
    seed_demo_data()  # must not fail or duplicate anything
    for account in ACCOUNTS:
        response = client.get(f"{URL}/{account['id']}")
        assert response.status_code == 200
        assert response.json()["sheba_number"] == account["sheba_number"]
        assert response.json()["status"] == account["status"]