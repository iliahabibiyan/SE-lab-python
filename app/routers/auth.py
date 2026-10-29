from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_schemas import LoginRequest, TokenResponse
from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ApiError
from app.models import User
from app.schemas import UserResponse
from app.security import hash_password, verify_password
from app.tokens import ACCESS_TOKEN_MINUTES, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

INVALID_CREDENTIALS = "کد ملی یا رمز عبور اشتباه است"
INACTIVE_MESSAGES = {
    "BLOCKED": "حساب کاربری مسدود شده است",
    "INACTIVE": "حساب کاربری غیرفعال است",
}
# Checked when the user does not exist, so the response time is the same as for a wrong password.
DUMMY_HASH = hash_password("dummy-password-for-timing")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """US2: log in with national code + password and get a JWT access token (only ACTIVE users)."""
    user = db.scalar(select(User).where(User.national_code == body.national_code))

    stored_hash = user.password_hash if user else None
    password_ok = verify_password(body.password, stored_hash or DUMMY_HASH)
    if user is None or stored_hash is None or not password_ok:
        raise ApiError(401, "UNAUTHORIZED", INVALID_CREDENTIALS)

    if user.status != "ACTIVE":
        raise ApiError(403, "FORBIDDEN", INACTIVE_MESSAGES.get(user.status, "حساب کاربری فعال نیست"))

    return TokenResponse(access_token=create_access_token(user.id), expires_in=ACCESS_TOKEN_MINUTES * 60)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Profile of the logged-in user. Also the simplest example of a protected endpoint."""
    return current_user