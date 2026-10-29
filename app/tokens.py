import os
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))


def get_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 16:
        raise RuntimeError("JWT_SECRET is not set (it must have at least 16 characters)")
    return secret


def _create_token(user_id: str, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "type": token_type, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, get_secret(), algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))


def decode_token(token: str, token_type: str = "access") -> dict:
    payload = jwt.decode(token, get_secret(), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload