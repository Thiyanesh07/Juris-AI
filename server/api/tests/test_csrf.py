from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import Settings
from app.core.csrf import CSRFMiddleware


def _client() -> TestClient:
    settings = Settings(
        frontend_url="https://juris-ai-user.vercel.app",
        extra_cors_origins="https://juris-ai-admin.vercel.app",
        session_secret="test-secret-key-32-chars-minimum-len",
    )
    test_app = FastAPI()

    @test_app.get("/admin/state")
    async def read_state(request: Request) -> dict[str, bool]:
        return {"authenticated": "user_id" in request.session}

    @test_app.post("/admin/state")
    async def write_state() -> dict[str, str]:
        return {"status": "changed"}

    @test_app.post("/auth/login")
    async def login(request: Request) -> dict[str, str]:
        request.session["user_id"] = "user-1"
        return {"status": "logged-in"}

    @test_app.post("/auth/logout")
    async def logout() -> None:
        return None

    test_app.add_middleware(CSRFMiddleware, settings=settings)
    test_app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    return TestClient(test_app)


def _authenticate(client: TestClient) -> None:
    assert client.post("/auth/login").status_code == 200


def test_allowed_trusted_origin_can_change_authenticated_state() -> None:
    with _client() as client:
        _authenticate(client)
        response = client.post(
            "/admin/state",
            headers={"Origin": "https://juris-ai-user.vercel.app"},
        )
        assert response.status_code == 200


def test_untrusted_origin_is_rejected_for_authenticated_admin_change() -> None:
    with _client() as client:
        _authenticate(client)
        response = client.post(
            "/admin/state",
            headers={"Origin": "https://evil.example"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "CSRF validation failed"


def test_missing_and_malformed_origin_or_referer_are_rejected() -> None:
    for headers in ({}, {"Origin": "not-an-origin"}, {"Referer": "javascript:alert(1)"}):
        with _client() as client:
            _authenticate(client)
            response = client.post("/admin/state", headers=headers)
            assert response.status_code == 403


def test_allowed_referer_is_accepted_and_safe_methods_are_unaffected() -> None:
    with _client() as client:
        _authenticate(client)
        assert client.get("/admin/state").status_code == 200
        response = client.post(
            "/admin/state",
            headers={"Referer": "https://juris-ai-admin.vercel.app/settings"},
        )
        assert response.status_code == 200


def test_authentication_flow_and_oauth_callback_paths_are_not_blocked() -> None:
    with _client() as client:
        assert client.post("/auth/login").status_code == 200
        response = client.post(
            "/auth/logout",
            headers={"Origin": "https://evil.example"},
        )
        assert response.status_code == 403
