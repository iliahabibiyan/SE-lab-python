import json
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("labbank")

# Base error codes from the project document (section 3.1)
DEFAULT_CODES = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
    504: "UPSTREAM_TIMEOUT",
}


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        detail: str,
        title: str | None = None,
        extra: dict | None = None,
        headers: dict | None = None,
    ):
        self.status = status
        self.code = code
        self.detail = detail
        self.title = title or code.replace("_", " ").capitalize()
        self.extra = extra or {}  # additional fields of the problem body
        self.headers = headers  # additional HTTP headers (e.g. Retry-After)


def problem_response(
    request: Request, status: int, code: str, title: str, detail: str, headers: dict | None = None, **extra
) -> JSONResponse:
    """RFC 9457 problem+json body, as required by GEN-06."""
    body = {
        "type": "https://errors.labbank.example/" + code.lower().replace("_", "-"),
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "correlation_id": getattr(request.state, "correlation_id", None),
        **extra,
    }
    return JSONResponse(body, status_code=status, headers=headers, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return problem_response(request, exc.status, exc.code, exc.title, exc.detail, exc.headers, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(p) for p in e["loc"][1:]),
                "message": e["msg"].removeprefix("Value error, "),
            }
            for e in exc.errors()
        ]
        return problem_response(
            request, 400, "VALIDATION_ERROR", "Validation error", "Invalid or incomplete input", errors=errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        code = DEFAULT_CODES.get(exc.status_code, "ERROR")
        return problem_response(request, exc.status_code, code, str(exc.detail), str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        # The message of the exception is neither returned nor logged: it may contain SQL parameters or other secrets.
        logger.error(
            json.dumps(
                {
                    "level": "ERROR",
                    "service": "S1-ACC",
                    "event": "unhandled_exception",
                    "error_type": type(exc).__name__,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "path": request.url.path,
                }
            )
        )
        return problem_response(request, 500, "INTERNAL_ERROR", "Internal error", "An unexpected error occurred")
