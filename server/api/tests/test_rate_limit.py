from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import Settings
from app.core.rate_limit import RateLimitMiddleware, client_identity


def _client(
    *,
    auth_limit: int = 2,
    qa_limit: int = 2,
    upload_limit: int = 2,
    trusted_proxy_ips: str = "",
    peer: tuple[str, int] = ("testclient", 50000),
) -> TestClient:
    settings = Settings(
        rate_limit_window_seconds=60,
        rate_limit_auth_requests=auth_limit,
        rate_limit_qa_requests=qa_limit,
        rate_limit_upload_requests=upload_limit,
        trusted_proxy_ips=trusted_proxy_ips,
        session_secret="test-secret-key-32-chars-minimum-len",
    )
    test_app = _build_app(settings)

    async def peer_app(scope: dict, receive: object, send: object) -> None:
        if scope["type"] == "http":
            scope = {**scope, "client": peer}
        await test_app(scope, receive, send)

    return TestClient(peer_app)


def _build_app(settings: Settings) -> FastAPI:
    test_app = FastAPI()

    @test_app.post("/auth/login")
    async def login() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.post("/qa/ask")
    async def qa(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    @test_app.post("/documents/upload")
    async def upload() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.post("/test-session/{user_id}")
    async def set_session(user_id: str, request: Request) -> dict[str, str]:
        request.session["user_id"] = user_id
        return {"status": "ok"}

    test_app.add_middleware(RateLimitMiddleware, settings=settings)
    test_app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    return test_app


def test_auth_requests_below_limit_succeed_and_exceeding_request_is_429() -> None:
    with _client(auth_limit=2) as client:
        assert client.post("/auth/login").status_code == 200
        response = client.post("/auth/login")
        assert response.status_code == 200
        limited = client.post("/auth/login")
        assert limited.status_code == 429
        assert limited.headers["retry-after"].isdigit()


def test_qa_and_upload_limits_are_independent() -> None:
    with _client(qa_limit=1, upload_limit=1) as client:
        assert client.post("/qa/ask").status_code == 200
        assert client.post("/qa/ask").status_code == 429
        assert client.post("/documents/upload").status_code == 200
        assert client.post("/documents/upload").status_code == 429


def test_authenticated_user_quota_is_shared_across_client_ips() -> None:
    settings = Settings(
        rate_limit_window_seconds=60,
        rate_limit_qa_requests=1,
        session_secret="test-secret-key-32-chars-minimum-len",
    )
    test_app = _build_app(settings)

    async def first_peer(scope: dict, receive: object, send: object) -> None:
        if scope["type"] == "http":
            scope = {**scope, "client": ("198.51.100.10", 8000)}
        await test_app(scope, receive, send)

    async def second_peer(scope: dict, receive: object, send: object) -> None:
        if scope["type"] == "http":
            scope = {**scope, "client": ("198.51.100.11", 8000)}
        await test_app(scope, receive, send)

    with TestClient(first_peer) as first:
        assert first.post("/test-session/shared-user").status_code == 200
        assert first.post("/qa/ask").status_code == 200
        session_cookie = first.cookies.get("session")

    with TestClient(second_peer) as second:
        second.cookies.set("session", session_cookie)
        response = second.post("/qa/ask")
        assert response.status_code == 429
        assert response.headers["retry-after"].isdigit()


def test_authenticated_users_have_independent_quotas() -> None:
    with _client(qa_limit=1, peer=("198.51.100.20", 8000)) as first:
        assert first.post("/test-session/user-one").status_code == 200
        assert first.post("/qa/ask").status_code == 200

    with _client(qa_limit=1, peer=("198.51.100.21", 8000)) as second:
        assert second.post("/test-session/user-two").status_code == 200
        assert second.post("/qa/ask").status_code == 200


def test_forwarded_for_is_ignored_without_trusted_proxy() -> None:
    with _client(auth_limit=1) as client:
        headers = {"X-Forwarded-For": "203.0.113.10"}
        assert client.post("/auth/login", headers=headers).status_code == 200
        assert client.post(
            "/auth/login", headers={"X-Forwarded-For": "203.0.113.11"}
        ).status_code == 429


def test_forwarded_for_is_used_only_from_trusted_proxy() -> None:
    settings = Settings(trusted_proxy_ips="127.0.0.1")
    request = Request(
        {
            "type": "http",
            "client": ("127.0.0.1", 8000),
            "headers": [(b"x-forwarded-for", b"203.0.113.10, 198.51.100.7")],
        }
    )
    assert client_identity(request, settings) == "198.51.100.7"

    untrusted_request = Request(
        {
            "type": "http",
            "client": ("192.0.2.1", 8000),
            "headers": [(b"x-forwarded-for", b"203.0.113.10")],
        }
    )
    assert client_identity(untrusted_request, settings) == "192.0.2.1"
