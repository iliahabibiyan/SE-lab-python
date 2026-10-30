import os
import time
import uuid
from datetime import datetime, timezone


def new_id() -> str:
    """Return a UUID version 7 as a string (time-ordered, as recommended by GEN-04)."""
    ms = int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = rand >> 68               # 12 bits
    rand_b = rand & ((1 << 62) - 1)   # 62 bits
    value = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return str(uuid.UUID(int=value))


def utcnow() -> datetime:
    """Current UTC time without tzinfo (the database columns store naive UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)