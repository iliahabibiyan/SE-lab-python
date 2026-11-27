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
        raise ApiError(401, "UNAUTHORIZED", "Token is missing")

    try:
        payload = decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:
        raise ApiError(401, "UNAUTHORIZED", "Token is invalid or expired") from None

    user = db.get(User, payload["sub"])
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "Token is invalid")

    if payload.get("ver", 0) != user.token_version:  # the user was blocked/deactivated after the token was issued
        raise ApiError(401, "UNAUTHORIZED", "Token was revoked; log in again")

    if user.status != "ACTIVE":  # e.g. blocked directly in the database
        raise ApiError(403, "FORBIDDEN", "Account is not active")

    return user


def require_roles(*roles: str):
    """Dependency factory: only logged-in users with one of `roles` may call the endpoint (403 for the others)."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "You are not allowed to do this")
        return current_user

    return checker