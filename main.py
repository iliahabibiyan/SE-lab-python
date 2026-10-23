"""Customer and Account Management Service - Main API."""
import psycopg
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from db import get_conn
from validators import UserCreateRequest, hash_password

app = FastAPI(
    title="Customer & Account Management Service",
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


@app.post("/api/v1/users", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreateRequest):
    password_hashed = hash_password(payload.password)
    query = """
        INSERT INTO users (
            national_id, full_name, birth_date, phone_number,
            address, postal_code, password_hash
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING user_id, national_id, full_name, birth_date, status,
                  phone_number, address, postal_code, created_at, updated_at;
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        payload.national_id,
                        payload.full_name,
                        payload.birth_date,
                        payload.phone_number,
                        payload.address,
                        payload.postal_code,
                        password_hashed,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "کاربری با این کد ملی یا شماره موبایل قبلاً ثبت شده است."},
        )

    return {
        "user_id": str(row[0]),
        "national_id": row[1],
        "full_name": row[2],
        "birth_date": row[3].isoformat(),
        "status": row[4],
        "phone_number": row[5],
        "address": row[6],
        "postal_code": row[7],
        "created_at": row[8].isoformat(),
        "updated_at": row[9].isoformat(),
    }
