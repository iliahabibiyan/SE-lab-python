import json
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.clients.s6_client import S6Client, S6Unavailable, get_s6_client
from app.database import get_db
from app.errors import ApiError
from app.models import Account
from app.schemas import AccountDetailResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])
logger = logging.getLogger("labbank")

ACCOUNT_NOT_FOUND = "حسابی با این شناسه یافت نشد"


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