from datetime import timedelta

import jwt
import pytest

from app.tokens import _create_token, create_access_token, decode_token

USER_ID = "0192a7e4-6b1d-7c3e-9a41-2f5d8e0b7c11"


def test_access_token_roundtrip():
    payload = decode_token(create_access_token(USER_ID))
    assert payload["sub"] == USER_ID
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_expired_token_is_rejected():
    token = _create_token(USER_ID, "access", timedelta(seconds=-60))
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token)


def test_tampered_token_is_rejected():
    header, payload, signature = create_access_token(USER_ID).split(".")
    changed = "A" if payload[-3] != "A" else "B"
    tampered = ".".join([header, payload[:-3] + changed + payload[-2:], signature])
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered)


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode({"sub": USER_ID, "type": "access", "exp": 9999999999}, "another-secret-key-0123456789-abcdef", algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(forged)


def test_wrong_token_type_is_rejected():
    token = _create_token(USER_ID, "refresh", timedelta(minutes=5))
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "access")
    assert decode_token(token, "refresh")["sub"] == USER_ID


def test_garbage_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not-a-jwt")