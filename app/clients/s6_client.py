import os
from typing import Protocol

import httpx


class S6Unavailable(Exception):
    """S6 did not answer in time, answered with an error, or its answer was not understood."""


class S6Client(Protocol):
    """What S1 needs from S6 (Reconciliation). Tests use a fake with the same method."""

    def get_exceptions(self, account_id: str, correlation_id: str | None = None) -> list[dict]: ...


class HttpS6Client:
    """Calls GET /api/v1/accounts/{id}/exceptions of S6. The base URL comes from NEIGHBOR_BASE_URL."""

    def __init__(self, base_url: str | None, timeout: float = 2.0):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    def get_exceptions(self, account_id: str, correlation_id: str | None = None) -> list[dict]:
        if not self.base_url:
            raise S6Unavailable("NEIGHBOR_BASE_URL is not set")
        headers = {"X-Correlation-ID": correlation_id} if correlation_id else {}
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/accounts/{account_id}/exceptions", headers=headers, timeout=self.timeout
            )
        except httpx.HTTPError as error:  # timeout, connection refused, ...
            raise S6Unavailable(str(error)) from error

        if response.status_code == 404:  # S6 does not know the account: no exceptions
            return []
        if response.status_code != 200:
            raise S6Unavailable(f"S6 answered {response.status_code}")
        try:
            return response.json()["items"]
        except (ValueError, KeyError, TypeError) as error:  # not JSON, or not the expected shape
            raise S6Unavailable("S6 answer has an unexpected shape") from error


def get_s6_client() -> S6Client:
    """FastAPI dependency; tests replace it with a fake (app.dependency_overrides)."""
    return HttpS6Client(os.getenv("NEIGHBOR_BASE_URL"))