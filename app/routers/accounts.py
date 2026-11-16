from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import Account
from app.schemas import AccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])

ACCOUNT_NOT_FOUND = "حسابی با این شناسه یافت نشد"


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: UUID, db: Session = Depends(get_db)):
    """Loop endpoint (S2 calls it): details and status of an account. Service to service, no user token."""
    account = db.get(Account, str(account_id))
    if account is None:
        raise ApiError(404, "NOT_FOUND", ACCOUNT_NOT_FOUND)
    return account