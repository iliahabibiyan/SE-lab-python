from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Base error codes from the project document (section 3.1)
DEFAULT_CODES = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    503: "SERVICE_UNAVAILABLE",
    504: "UPSTREAM_TIMEOUT",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, detail: str, title: str | None = None):
        self.status = status
        self.code = code
        self.detail = detail
        self.title = title or code.replace("_", " ").capitalize()


def problem_response(request: Request, status: int, code: str, title: str, detail: str, **extra) -> JSONResponse:
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
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return problem_response(request, exc.status, exc.code, exc.title, exc.detail)

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