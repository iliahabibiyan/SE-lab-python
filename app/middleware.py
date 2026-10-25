import json
import logging
from datetime import datetime, timezone

from fastapi import Request

from app.utils import new_id

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("labbank")


async def correlation_middleware(request: Request, call_next):
    """GEN-08 / GEN-11: keep X-Correlation-ID and write one JSON log line per request."""
    correlation_id = request.headers.get("X-Correlation-ID") or new_id()
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(
        json.dumps(
            {
                "level": "INFO",
                "time": datetime.now(timezone.utc).isoformat(),
                "service": "S1-ACC",
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            }
        )
    )
    return response