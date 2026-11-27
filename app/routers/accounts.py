import json
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clients.s2_client import S2Client, S2Unavailable, get_s2_client
from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ApiError
from app.iban import generate_sheba
from app.models import Account, User
from app.permissions import ensure_can_open_account
from app.schemas import AccountCreate, AccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])
logger = logging.getLogger("labbank")

MAX_ACCOUNTS_PER_USER = int(os.getenv("MAX_ACCOUNTS_PER_USER", "5"))

ACCOUNT_NOT_FOUND = "Account not found"
USER_NOT_FOUND = "User not found"


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: UUID, db: Session = Depends(get_db)):
    """Details and status of an account. Service to service call (for example S2): no user token."""
    account = db.get(Account, str(account_id))
    if account is None:
        raise ApiError(404, "NOT_FOUND", ACCOUNT_NOT_FOUND)
    return account


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(
    body: AccountCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    s2: S2Client = Depends(get_s2_client),
):
    """US6: open a new account for an ACTIVE user. A customer opens it for himself; staff for anybody."""
    owner_id = str(body.user_id)
    ensure_can_open_account(current_user, owner_id)  # before the lookup: no hint whether the id exists

    # with_for_update locks the row of the owner (PostgreSQL): two requests that open an account for the same user
    # at the same time wait for each other, so both can not pass the limit check below together.
    owner = db.get(User, owner_id, with_for_update=True)

    if owner is None:
        raise ApiError(404, "NOT_FOUND", USER_NOT_FOUND)
    if owner.status != "ACTIVE":
        raise ApiError(400, "USER_NOT_ACTIVE", "The owner of the account must be an ACTIVE user")

    accounts_of_owner = db.scalar(select(func.count()).select_from(Account).where(Account.user_id == owner_id))
    if accounts_of_owner >= MAX_ACCOUNTS_PER_USER:
        raise ApiError(409, "CONFLICT", f"A user can have at most {MAX_ACCOUNTS_PER_USER} accounts")

    for _ in range(5):  # a Sheba collision is practically impossible, but the database would refuse it
        account = Account(user_id=owner_id, sheba_number=generate_sheba(), account_type=body.account_type)
        db.add(account)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(account)
        try:
            s2.account_created(account.id, request.state.correlation_id)
        except S2Unavailable as error:  # S2 must not break opening an account (BO-05); retrying later is another task
            logger.warning(
                json.dumps(
                    {
                        "level": "WARNING",
                        "service": "S1-ACC",
                        "event": "s2_unavailable",
                        "correlation_id": request.state.correlation_id,
                        "account_id": account.id,
                        "error": str(error),
                    }
                )
            )
        return account
    raise ApiError(503, "SERVICE_UNAVAILABLE", "Could not generate a Sheba number; try again")
