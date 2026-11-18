from app.clients.s2_client import S2Unavailable


class FakeS2Client:
    """Stands in for S2 in tests: no network."""

    def __init__(self, down: bool = False):
        self.down = down
        self.calls: list[tuple[str, str | None]] = []

    def account_created(self, account_id: str, correlation_id: str | None = None) -> None:
        self.calls.append((account_id, correlation_id))
        if self.down:
            raise S2Unavailable("fake S2 is down")