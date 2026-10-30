import math
import os
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth_schemas import LoginRequest, RefreshRequest, TokenResponse
from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ApiError
from app.models import User
from app.schemas import UserResponse
from app.security import hash_password, verify_password
from app.tokens import ACCESS_TOKEN_MINUTES, create_access_token, create_refresh_token, decode_token
from app.utils import utcnow

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))

INVALID_CREDENTIALS = "کد ملی یا رمز عبور اشتباه است"
LOCKED_MESSAGE = "به دلیل تلاش‌های ناموفق زیاد، ورود موقتاً مسدود شده است؛ بعداً دوباره تلاش کنید"
INACTIVE_MESSAGES = {
    "BLOCKED": "حساب کاربری مسدود شده است",
    "INACTIVE": "حساب کاربری غیرفعال است",
}
DUMMY_HASH = hash_password("dummy-password-for-timing")


def build_tokens(user_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )


def register_failed_attempt(db: Session, user: User, now: datetime) -> None:
    """Count one wrong password; lock the account when the limit is reached."""
    db.execute(
        update(User).where(User.id == user.id).values(failed_login_attempts=User.failed_login_attempts + 1)
    )
    db.commit()
    db.refresh(user)
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.failed_login_attempts = 0
        user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
        db.commit()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """US2: log in with national code + password and get a JWT access token (only ACTIVE users)."""
    user = db.scalar(select(User).where(User.national_code == body.national_code))
    now = utcnow()

    # 1) temporarily locked after too many wrong passwords
    if user is not None and user.locked_until is not None and user.locked_until > now:
        retry_after = max(1, math.ceil((user.locked_until - now).total_seconds()))
        raise ApiError(
            429,
            "LOGIN_TEMPORARILY_LOCKED",
            LOCKED_MESSAGE,
            extra={"retry_after_seconds": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # 2) check the password
    stored_hash = user.password_hash if user else None
    password_ok = verify_password(body.password, stored_hash or DUMMY_HASH)
    if user is None or stored_hash is None or not password_ok:
        if user is not None:
            register_failed_attempt(db, user, now)
        raise ApiError(401, "UNAUTHORIZED", INVALID_CREDENTIALS)

    # 3) correct password: reset the counter
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()

    # 4) only ACTIVE users get a token
    if user.status != "ACTIVE":
        raise ApiError(403, "FORBIDDEN", INACTIVE_MESSAGES.get(user.status, "حساب کاربری فعال نیست"))

    return build_tokens(user.id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new pair of tokens, without logging in again."""
    try:
        payload = decode_token(body.refresh_token, "refresh")
    except jwt.InvalidTokenError:
        raise ApiError(401, "UNAUTHORIZED", "توکن نامعتبر یا منقضی شده است")

    user = db.get(User, payload["sub"])
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "توکن نامعتبر است")
    if user.status != "ACTIVE":  # blocked/inactive users can not extend their session
        raise ApiError(403, "FORBIDDEN", INACTIVE_MESSAGES.get(user.status, "حساب کاربری فعال نیست"))
    return build_tokens(user.id)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Profile of the logged-in user. Also the simplest example of a protected endpoint."""
    return current_user