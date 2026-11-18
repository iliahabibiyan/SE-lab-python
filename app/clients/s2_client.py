import os
from typing import Protocol

import httpx


class S2Unavailable(Exception):
    """S2 did not answer in time, answered with an error, or its address is not configured."""


class S2Client(Protocol):
    """What S1 tells S2 (Ledger). Tests use a fake with the same method."""

    def account_created(self, account_id: str, correlation_id: str | None = None) -> None: ...


class HttpS2Client:
    """Calls POST /api/v1/accounts of S2 (contract: account created). The base URL comes from S2_BASE_URL."""

    def __init__(self, base_url: str | None, timeout: float = 2.0):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    def account_created(self, account_id: str, correlation_id: str | None = None) -> None:
        if not self.base_url:
            raise S2Unavailable("S2_BASE_URL is not set")
        headers = {"Idempotency-Key": account_id}  # a retry with the same key is harmless for S2
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/accounts", json={"account_id": account_id}, headers=headers, timeout=self.timeout
            )
        except httpx.HTTPError as error:  # timeout, connection refused, ...
            raise S2Unavailable(str(error)) from error
        if response.status_code not in (200, 201, 204):
            raise S2Unavailable(f"S2 answered {response.status_code}")


def get_s2_client() -> S2Client:
    """FastAPI dependency; tests replace it with a fake (app.dependency_overrides)."""
    return HttpS2Client(os.getenv("S2_BASE_URL"))