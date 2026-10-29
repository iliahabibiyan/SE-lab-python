import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.tokens import decode_token

# auto_error=False: a missing header is reported by us, in the standard problem+json format
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Use it in any endpoint that needs a logged-in user: `user: User = Depends(get_current_user)`."""
    if credentials is None:
        raise ApiError(401, "UNAUTHORIZED", "توکن ارسال نشده است")

    try:
        payload = decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:
        raise ApiError(401, "UNAUTHORIZED", "توکن نامعتبر یا منقضی شده است")

    user = db.get(User, payload["sub"])
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "توکن نامعتبر است")

    if user.status != "ACTIVE":  # e.g. blocked after the token was issued
        raise ApiError(403, "FORBIDDEN", "حساب کاربری فعال نیست")

    return user
