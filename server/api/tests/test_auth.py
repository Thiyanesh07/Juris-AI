"""Authentication and authorization tests (Google OAuth, sessions, roles, disabled status)."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_super_admin
from app.auth.google import GoogleIdentity, find_or_create_user
from app.auth.password import hash_password
from app.cli import _create_super_admin
from app.core.config import Settings, get_settings
from app.main import app
from app.models import User, UserRole

_test_router = APIRouter(prefix="/test-roles", tags=["test"])


@_test_router.get("/admin")
async def admin_only_endpoint(user: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok", "role": user.role.value, "user_id": str(user.id)}


@_test_router.get("/super-admin")
async def super_admin_only_endpoint(user: User = Depends(require_super_admin)) -> dict[str, str]:
    return {"status": "ok", "role": user.role.value, "user_id": str(user.id)}


app.include_router(_test_router)


def _mock_settings() -> Settings:
    return Settings(
        session_secret="test-secret-key-32-chars-minimum-len",
        frontend_url="http://localhost:5173",
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
        google_redirect_uri="http://localhost:5173/auth/google/callback",
    )


@pytest.fixture(autouse=True)
def override_settings() -> Iterator[None]:
    app.dependency_overrides[get_settings] = _mock_settings
    yield
    app.dependency_overrides.pop(get_settings, None)


def test_auth_me_unauthenticated(client: TestClient) -> None:
    client.cookies.clear()
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_register_login_and_me(client: TestClient) -> None:
    email = f"user-{uuid4().hex[:8]}@example.com"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Test User"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["email"] == email
    assert body["name"] == "Test User"
    assert body["role"] == "user"
    assert body["is_active"] is True

    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    client.post("/auth/logout")
    client.cookies.clear()

    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    assert client.get("/auth/me").json()["email"] == email


def test_google_login_redirect_url(client: TestClient) -> None:
    response = client.get("/auth/google/login?state=/home", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers.get("location", "")
    assert "https://accounts.google.com/o/oauth2/v2/auth" in location
    assert "client_id=test-client-id" in location
    assert "state=intent%3Dsignin" in location



def test_google_login_json_response(client: TestClient) -> None:
    response = client.get("/auth/google/login?state=/home", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "https://accounts.google.com/o/oauth2/v2/auth" in data["url"]


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_success(mock_exchange: AsyncMock, client: TestClient) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject="google-sub-12345",
        email="googleuser@example.com",
        name="Google User",
        image_url="https://lh3.googleusercontent.com/a/photo.jpg",
    )

    # First sign up
    res = client.get("/auth/google/callback?code=mock-code&intent=signup&state=/home")
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["email"] == "googleuser@example.com"
    assert user_data["name"] == "Google User"
    assert user_data["role"] == "user"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "googleuser@example.com"

    client.post("/auth/logout")
    client.cookies.clear()

    # Next sign in with existing user succeeds
    res_signin = client.get("/auth/google/callback?code=mock-code&intent=signin&state=/home")
    assert res_signin.status_code == 200
    assert res_signin.json()["email"] == "googleuser@example.com"


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_signin_intent_no_account(mock_exchange: AsyncMock, client: TestClient) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject="google-sub-unknown",
        email="unknown@example.com",
        name="Unknown User",
        image_url=None,
    )
    res = client.get("/auth/google/callback?code=mock-code&intent=signin&state=/home")
    assert res.status_code == 404
    assert "No Juris AI account found" in res.json()["detail"]


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_signup_intent_duplicate_account(mock_exchange: AsyncMock, client: TestClient) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject="google-sub-dup",
        email="dup@example.com",
        name="Dup User",
        image_url=None,
    )
    # Register once
    client.get("/auth/google/callback?code=mock-code&intent=signup&state=/home")
    client.post("/auth/logout")
    client.cookies.clear()

    # Attempt second signup with same Google account
    res_signup = client.get("/auth/google/callback?code=mock-code&intent=signup&state=/home")
    assert res_signup.status_code == 409
    assert "already has a Juris AI account" in res_signup.json()["detail"]


from sqlalchemy import select

def test_disabled_user_login_blocked(client: TestClient) -> None:
    disabled_user = User(
        id=uuid4(),
        email="disabled-user@example.com",
        role=UserRole.USER,
        is_active=False,
    )
    # When get_current_user returns a disabled user or is called with disabled user session
    app.dependency_overrides[get_current_user] = lambda: disabled_user
    try:
        res = client.get("/auth/me")
        assert res.status_code == 401
        assert res.json()["detail"] == "Account is disabled"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_role_enforcement_hierarchy(client: TestClient) -> None:
    norm_user = User(id=uuid4(), email="user@example.com", role=UserRole.USER, is_active=True)
    admin_user = User(id=uuid4(), email="admin@example.com", role=UserRole.ADMIN, is_active=True)
    super_admin_user = User(id=uuid4(), email="superadmin@example.com", role=UserRole.SUPER_ADMIN, is_active=True)

    # USER
    app.dependency_overrides[get_current_user] = lambda: norm_user
    try:
        assert client.get("/test-roles/admin").status_code == 403
        assert client.get("/test-roles/super-admin").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # ADMIN
    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        assert client.get("/test-roles/admin").status_code == 200
        assert client.get("/test-roles/super-admin").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # SUPER_ADMIN
    app.dependency_overrides[get_current_user] = lambda: super_admin_user
    try:
        assert client.get("/test-roles/admin").status_code == 200
        assert client.get("/test-roles/super-admin").status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_create_super_admin_cli(session: AsyncSession) -> None:
    email = f"super-{uuid4().hex[:8]}@example.com"
    with patch("app.cli.session_factory", return_value=session):
        code = await _create_super_admin(email=email, name="Chief Admin")
        assert code == 0

    user = await session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.role is UserRole.SUPER_ADMIN
    assert user.is_active is True
    assert user.name == "Chief Admin"
