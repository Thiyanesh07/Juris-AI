"""Authentication and authorization tests (Google OAuth, sessions, roles, disabled status)."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_super_admin
from app.auth.google import GoogleIdentity
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


def _begin_google_oauth(client: TestClient, *, intent: str, return_to: str = "/home") -> str:
    response = client.get(
        "/auth/google/login",
        params={
            "intent": intent,
            "return_to": return_to,
            "redirect_uri": "http://localhost:5173/auth/google/callback",
        },
        follow_redirects=False,
    )
    assert response.status_code == 307
    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    assert len(state) >= 32
    return state


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

    client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    client.cookies.clear()

    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    assert client.get("/auth/me").json()["email"] == email


def test_google_login_redirect_url(client: TestClient) -> None:
    response = client.get("/auth/google/login?return_to=/home", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers.get("location", "")
    assert "https://accounts.google.com/o/oauth2/v2/auth" in location
    assert "client_id=test-client-id" in location
    state = parse_qs(urlparse(location).query)["state"][0]
    assert len(state) >= 32
    assert state != "/home"



def test_google_login_json_response(client: TestClient) -> None:
    response = client.get("/auth/google/login?state=/home", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "https://accounts.google.com/o/oauth2/v2/auth" in data["url"]


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_success(mock_exchange: AsyncMock, client: TestClient) -> None:
    client.cookies.clear()
    mock_exchange.return_value = GoogleIdentity(
        subject="google-sub-12345",
        email="googleuser@example.com",
        name="Google User",
        image_url="https://lh3.googleusercontent.com/a/photo.jpg",
    )

    # First sign up
    state = _begin_google_oauth(client, intent="signup")
    res = client.get(f"/auth/google/callback?code=mock-code&state={state}")
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["email"] == "googleuser@example.com"
    assert user_data["name"] == "Google User"
    assert user_data["role"] == "user"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "googleuser@example.com"

    client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    client.cookies.clear()

    # Next sign in with existing user succeeds
    signin_state = _begin_google_oauth(client, intent="signin")
    res_signin = client.get(f"/auth/google/callback?code=mock-code&state={signin_state}")
    assert res_signin.status_code == 200
    assert res_signin.json()["email"] == "googleuser@example.com"


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_signin_intent_no_account(
    mock_exchange: AsyncMock, client: TestClient
) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject="google-sub-unknown",
        email="unknown@example.com",
        name="Unknown User",
        image_url=None,
    )
    state = _begin_google_oauth(client, intent="signin")
    res = client.get(f"/auth/google/callback?code=mock-code&state={state}")
    assert res.status_code == 404
    assert "No Juris AI account found" in res.json()["detail"]


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_signup_intent_duplicate_account(
    mock_exchange: AsyncMock, client: TestClient
) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject="google-sub-dup",
        email="dup@example.com",
        name="Dup User",
        image_url=None,
    )
    # Register once
    state = _begin_google_oauth(client, intent="signup")
    client.get(f"/auth/google/callback?code=mock-code&state={state}")
    client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    client.cookies.clear()

    # Attempt second signup with same Google account
    signup_state = _begin_google_oauth(client, intent="signup")
    res_signup = client.get(f"/auth/google/callback?code=mock-code&state={signup_state}")
    assert res_signup.status_code == 409
    assert "already has a Juris AI account" in res_signup.json()["detail"]


def test_google_callback_rejects_missing_and_mismatched_state(client: TestClient) -> None:
    state = _begin_google_oauth(client, intent="signin")

    missing = client.get("/auth/google/callback?code=mock-code")
    assert missing.status_code == 400
    assert missing.json()["detail"] == "Invalid OAuth state"

    _begin_google_oauth(client, intent="signin")
    mismatched = client.get("/auth/google/callback?code=mock-code&state=wrong-state")
    assert mismatched.status_code == 400
    assert mismatched.json()["detail"] == "Invalid OAuth state"
    assert state != "wrong-state"


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_rejects_replayed_state(
    mock_exchange: AsyncMock, client: TestClient
) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject=f"google-replay-{uuid4().hex}",
        email=f"replay-{uuid4().hex}@example.com",
        name="Replay User",
        image_url=None,
    )
    state = _begin_google_oauth(client, intent="signup")
    first = client.get(f"/auth/google/callback?code=mock-code&state={state}")
    assert first.status_code == 200

    replay = client.get(f"/auth/google/callback?code=mock-code&state={state}")
    assert replay.status_code == 400
    assert replay.json()["detail"] == "Invalid OAuth state"


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_callback_rejects_state_from_another_browser_session(
    mock_exchange: AsyncMock, client: TestClient
) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject=f"google-independent-{uuid4().hex}",
        email=f"independent-{uuid4().hex}@example.com",
        name="Independent User",
        image_url=None,
    )
    state = _begin_google_oauth(client, intent="signup")
    with TestClient(app) as other_client:
        response = other_client.get(f"/auth/google/callback?code=mock-code&state={state}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OAuth state"


@patch("app.api.routes.auth.exchange_code_for_identity")
def test_google_oauth_uses_opaque_state_for_invalid_return_path(
    mock_exchange: AsyncMock, client: TestClient
) -> None:
    mock_exchange.return_value = GoogleIdentity(
        subject=f"google-return-{uuid4().hex}",
        email=f"return-{uuid4().hex}@example.com",
        name="Return User",
        image_url=None,
    )
    state = _begin_google_oauth(
        client,
        intent="signup",
        return_to="https://evil.example/steal",
    )
    assert "evil.example" not in state
    response = client.get(f"/auth/google/callback?code=mock-code&state={state}")
    assert response.status_code == 200


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
    super_admin_user = User(
        id=uuid4(),
        email="superadmin@example.com",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )

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


@patch("app.api.routes.auth.exchange_code_for_identity")
async def test_admin_oauth_lifecycle(
    mock_exchange: AsyncMock, client: TestClient, session: AsyncSession
) -> None:
    """Test callback validation, login initiation, callback handling, session persistence, admin access, and logout."""
    client.cookies.clear()
    admin_callback = "http://localhost:3001/admin/auth/google/callback"

    # 1. Reject invalid redirect_uri
    invalid_login = client.get(
        "/auth/google/login",
        params={"intent": "signin", "redirect_uri": "http://evil.com/callback"},
    )
    assert invalid_login.status_code == 400
    assert invalid_login.json()["detail"] == "Invalid OAuth redirect URI"

    # 2. Login initiation with admin callback
    login_res = client.get(
        "/auth/google/login",
        params={"intent": "signup", "redirect_uri": admin_callback, "return_to": "/admin"},
        follow_redirects=False,
    )
    assert login_res.status_code == 307
    location = login_res.headers["location"]
    query_params = parse_qs(urlparse(location).query)
    assert query_params["redirect_uri"][0] == admin_callback
    state = query_params["state"][0]

    # 3. Successful callback with admin redirect_uri
    admin_email = f"admin-{uuid4().hex[:8]}@example.com"
    mock_exchange.return_value = GoogleIdentity(
        subject=f"google-admin-{uuid4().hex[:8]}",
        email=admin_email,
        name="Admin Test User",
        image_url=None,
    )
    cb_res = client.get(
        f"/auth/google/callback?code=mock-code&state={state}&redirect_uri={admin_callback}"
    )
    assert cb_res.status_code == 200
    user_body = cb_res.json()
    assert user_body["email"] == admin_email

    # 4. Session persistence via /auth/me
    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == admin_email

    # Promote user to ADMIN in the test database to verify admin access
    user = await session.scalar(select(User).where(User.email == admin_email))
    assert user is not None
    user.role = UserRole.ADMIN
    await session.commit()

    # Admin protected route access check
    admin_gate = client.get("/test-roles/admin")
    assert admin_gate.status_code == 200
    assert admin_gate.json()["role"] == "admin"

    # 5. Logout clears session
    logout_res = client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    assert logout_res.status_code == 204
    client.cookies.clear()

    # Protected admin access now rejected
    after_logout = client.get("/test-roles/admin")
    assert after_logout.status_code == 401


def test_production_oauth_allowlist_validation() -> None:
    """Verify that allowed_redirect_uris strictly accepts production admin and user callbacks and rejects invalid paths."""
    from app.auth.google import allowed_redirect_uris, validate_redirect_uri
    from fastapi import HTTPException

    prod_settings = Settings(
        app_env="production",
        session_secret="prod-secret-minimum-32-characters-length",
        session_cookie_secure=True,
        google_client_id="prod-client",
        google_client_secret="prod-secret",
        google_redirect_uri="https://juris-ai-user.vercel.app/auth/google/callback",
        google_allowed_redirect_uris="https://juris-ai-admin.vercel.app/auth/google/callback",
    )
    allowed = allowed_redirect_uris(prod_settings)
    assert "https://juris-ai-admin.vercel.app/admin/auth/google/callback" in allowed
    assert "https://juris-ai-user.vercel.app/auth/google/callback" in allowed

    # Validated without error
    validated = validate_redirect_uri(prod_settings, "https://juris-ai-admin.vercel.app/admin/auth/google/callback")
    assert validated == "https://juris-ai-admin.vercel.app/admin/auth/google/callback"

    # Insecure HTTP rejected in production
    with pytest.raises(HTTPException) as exc:
        validate_redirect_uri(prod_settings, "http://juris-ai-admin.vercel.app/admin/auth/google/callback")
    assert exc.value.status_code == 400

    # Arbitrary domain rejected
    with pytest.raises(HTTPException) as exc:
        validate_redirect_uri(prod_settings, "https://attacker.com/admin/auth/google/callback")
    assert exc.value.status_code == 400
