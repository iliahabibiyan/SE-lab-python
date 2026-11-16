import json
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_current_user
from app.iban import generate_sheba
from app.permissions import ensure_can_open_account
from app.clients.s6_client import S6Client, S6Unavailable, get_s6_client
from app.database import get_db
from app.errors import ApiError
from app.models import Account, User
from app.schemas import AccountCreate, AccountDetailResponse, AccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])
logger = logging.getLogger("labbank")

ACCOUNT_NOT_FOUND = "حسابی با این شناسه یافت نشد"
USER_NOT_FOUND = "کاربری با این شناسه یافت نشد"


@router.get("/{account_id}", response_model=AccountDetailResponse, response_model_exclude_none=True)
def get_account(
    account_id: UUID,
    request: Request,
    include: Literal["exceptions"] | None = Query(None, description="ask for extra data: exceptions (from S6)"),
    db: Session = Depends(get_db),
    s6: S6Client = Depends(get_s6_client),
):
    """Loop endpoint (S2 calls it): details and status of an account. Service to service, no user token.

    With ?include=exceptions S1 also asks S6; if S6 is down the account is still returned.
    """
    account = db.get(Account, str(account_id))
    if account is None:
        raise ApiError(404, "NOT_FOUND", ACCOUNT_NOT_FOUND)

    result = AccountDetailResponse.model_validate(account)
    if include == "exceptions":
        try:
            result.exceptions = s6.get_exceptions(str(account_id), request.state.correlation_id)
            result.exceptions_available = True
        except S6Unavailable as error:  # a neighbor problem must not break our own answer
            result.exceptions_available = False
            logger.warning(
                json.dumps(
                    {
                        "level": "WARNING",
                        "service": "S1-ACC",
                        "event": "s6_unavailable",
                        "correlation_id": request.state.correlation_id,
                        "account_id": str(account_id),
                        "error": str(error),
                    }
                )
            )
    return result


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(
    body: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """US6: open a new account for an ACTIVE user. A customer opens it for himself; staff for anybody."""
    owner_id = str(body.user_id)
    ensure_can_open_account(current_user, owner_id)  # before the lookup: no hint whether the id exists

    owner = db.get(User, owner_id)
    if owner is None:
        raise ApiError(404, "NOT_FOUND", USER_NOT_FOUND)
    if owner.status != "ACTIVE":
        raise ApiError(400, "USER_NOT_ACTIVE", "وضعیت کاربر صاحب حساب باید ACTIVE باشد")

    for _ in range(5):  # a Sheba collision is practically impossible, but the database would refuse it
        account = Account(user_id=owner_id, sheba_number=generate_sheba())
        db.add(account)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(account)
        return account
    raise ApiError(503, "SERVICE_UNAVAILABLE", "ساخت شماره شبا ممکن نشد؛ دوباره تلاش کنید")