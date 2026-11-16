from app.clients.s6_client import S6Unavailable


class FakeS6Client:
    """Stands in for S6 in tests: no network."""

    def __init__(self, exceptions: list[dict] | None = None, down: bool = False):
        self.exceptions = exceptions or []
        self.down = down
        self.calls: list[tuple[str, str | None]] = []

    def get_exceptions(self, account_id: str, correlation_id: str | None = None) -> list[dict]:
        self.calls.append((account_id, correlation_id))
        if self.down:
            raise S6Unavailable("fake S6 is down")
        return self.exceptions