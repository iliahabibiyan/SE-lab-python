from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import register_error_handlers
from app.middleware import correlation_middleware


def make_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(correlation_middleware)
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail that must not leak")

    return app


def test_unexpected_error_is_a_problem_details_500():
    client = TestClient(make_app(), raise_server_exceptions=False)  # return the 500 instead of re-raising it
    response = client.get("/boom")
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 500
    assert body["code"] == "INTERNAL_ERROR"
    assert "correlation_id" in body


def test_unexpected_error_does_not_leak_the_message():
    client = TestClient(make_app(), raise_server_exceptions=False)
    assert "secret detail" not in client.get("/boom").text
