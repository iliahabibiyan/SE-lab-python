"""Minimal health endpoint for the Software Engineering Lab."""
from fastapi.responses import JSONResponse
from db import get_conn
from fastapi import FastAPI

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
        return {"status": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})