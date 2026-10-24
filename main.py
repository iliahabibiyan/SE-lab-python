"""ACC1-S service: health and readiness endpoints."""
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from db import get_conn

logger = logging.getLogger("acc1-service")

app = FastAPI(
    title="Starter Service",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        logger.error("readiness check failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}