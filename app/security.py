import os

import bcrypt

# Work factor of bcrypt. 12 is a good default; tests set it to 4 to run fast.
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash (a string starting with $2b$). The password itself is never stored."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """True only if the password matches the hash. Never raises for bad input."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False