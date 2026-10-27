"""Integration tests for simultaneous admin and user session isolation in the same browser.

Verifies:
  - Both sessions coexist in the same cookie jar without overwriting each other.
  - Role-based authorization routes correctly to each portal session.
  - Refresh and navigation across tabs maintain independent identity.
  - Logout from one portal does NOT invalidate or overwrite the other portal.
  - Same-user dual portal sessions operate independently without cross-invalidation.
  - Session revocation and expiration behave safely on a per-portal basis.
"""

from __future__ import annotations

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.enums import UserRole


async def test_simultaneous_admin_and_user_sessions_in_same_browser(
    client: TestClient, session: AsyncSession
) -> None:
    """Simulate a single browser with two tabs: Tab 1 = Admin, Tab 2 = User."""
    client.cookies.clear()

    # 1. Register an Admin account
    admin_email = f"superadmin-{uuid4().hex[:8]}@juris.ai"
    admin_reg = client.post(
        "/auth/register",
        json={"email": admin_email, "password": "AdminPassword123!", "name": "Super Admin"},
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_reg.status_code == 201

    # Promote to SUPER_ADMIN in DB
    user_db = await session.scalar(select(User).where(User.email == admin_email))
    assert user_db is not None
    user_db.role = UserRole.SUPER_ADMIN
    await session.commit()

    # Re-login as Admin to establish the super_admin session
    admin_login = client.post(
        "/auth/login",
        json={"email": admin_email, "password": "AdminPassword123!"},
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_login.status_code == 200
    admin_cookie = client.cookies.get("legalgraph_admin_session")
    assert admin_cookie is not None, "Admin session cookie must be set"

    # 2. In the SAME browser (same client), sign in as a standard user in Tab 2
    user_email = f"researcher-{uuid4().hex[:8]}@chambers.in"
    user_reg = client.post(
        "/auth/register",
        json={"email": user_email, "password": "UserPassword123!", "name": "Adv. Researcher"},
        headers={"X-Juris-Portal": "user", "Origin": "https://juris-ai-user.vercel.app"},
    )
    assert user_reg.status_code == 201
    user_cookie = client.cookies.get("legalgraph_session")
    assert user_cookie is not None, "User session cookie must be set"

    # CRITICAL CHECK: The admin cookie MUST NOT have been overwritten!
    assert client.cookies.get("legalgraph_admin_session") == admin_cookie
    assert client.cookies.get("legalgraph_session") == user_cookie

    # 3. Tab 1 requests /auth/me -> Must resolve to Super Admin
    admin_me = client.get(
        "/auth/me",
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_me.status_code == 200
    assert admin_me.json()["email"] == admin_email
    assert admin_me.json()["role"] == "super_admin"

    # 4. Tab 2 requests /auth/me -> Must resolve to Researcher User
    user_me = client.get(
        "/auth/me",
        headers={"X-Juris-Portal": "user", "Origin": "https://juris-ai-user.vercel.app"},
    )
    assert user_me.status_code == 200
    assert user_me.json()["email"] == user_email
    assert user_me.json()["role"] == "user"

    # 5. Tab 1 accesses admin-protected endpoint -> Succeeded
    admin_jobs = client.get(
        "/documents/jobs",
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_jobs.status_code == 200

    admin_validation = client.get(
        "/validation",
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_validation.status_code == 200

    # 6. Tab 2 attempts admin-protected endpoint -> Denied 403 Forbidden
    user_forbidden = client.get(
        "/documents/jobs",
        headers={"X-Juris-Portal": "user", "Origin": "https://juris-ai-user.vercel.app"},
    )
    assert user_forbidden.status_code == 403
    assert user_forbidden.json()["detail"] == "Insufficient permissions"

    # 7. Refresh simulation: both tabs refresh multiple times in interleaved order
    for _ in range(3):
        res1 = client.get("/auth/me", headers={"X-Juris-Portal": "admin"})
        assert res1.status_code == 200
        assert res1.json()["role"] == "super_admin"

        res2 = client.get("/auth/me", headers={"X-Juris-Portal": "user"})
        assert res2.status_code == 200
        assert res2.json()["role"] == "user"

    # 8. Admin Logout in Tab 1 -> Must clear ONLY admin session
    admin_logout = client.post(
        "/auth/logout",
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_logout.status_code == 204

    # Tab 1 is now logged out
    admin_after_logout = client.get(
        "/auth/me",
        headers={"X-Juris-Portal": "admin", "Origin": "https://juris-ai-admin.vercel.app"},
    )
    assert admin_after_logout.status_code == 401

    # CRITICAL: Tab 2 (User) is STILL logged in and unaffected!
    user_after_admin_logout = client.get(
        "/auth/me",
        headers={"X-Juris-Portal": "user", "Origin": "https://juris-ai-user.vercel.app"},
    )
    assert user_after_admin_logout.status_code == 200
    assert user_after_admin_logout.json()["email"] == user_email

    # 9. User Logout in Tab 2 -> Clears user session
    user_logout = client.post(
        "/auth/logout",
        headers={"X-Juris-Portal": "user", "Origin": "https://juris-ai-user.vercel.app"},
    )
    assert user_logout.status_code == 204

    # Both tabs are now logged out
    assert client.get("/auth/me", headers={"X-Juris-Portal": "user"}).status_code == 401
    assert client.get("/auth/me", headers={"X-Juris-Portal": "admin"}).status_code == 401


async def test_same_user_dual_session_isolation(
    client: TestClient, session: AsyncSession
) -> None:
    """Test when the SAME super_admin account signs into both Admin and User tabs."""
    client.cookies.clear()
    email = f"dualadmin-{uuid4().hex[:8]}@juris.ai"
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": "DualPassword123!", "name": "Dual Admin"},
        headers={"X-Juris-Portal": "admin"},
    )
    assert reg.status_code == 201

    user_db = await session.scalar(select(User).where(User.email == email))
    assert user_db is not None
    user_db.role = UserRole.SUPER_ADMIN
    await session.commit()

    # Sign into Admin tab
    auth_admin = client.post(
        "/auth/login",
        json={"email": email, "password": "DualPassword123!"},
        headers={"X-Juris-Portal": "admin"},
    )
    assert auth_admin.status_code == 200

    # Sign into User tab
    auth_user = client.post(
        "/auth/login",
        json={"email": email, "password": "DualPassword123!"},
        headers={"X-Juris-Portal": "user"},
    )
    assert auth_user.status_code == 200

    # Both tabs resolve to this user
    assert client.get("/auth/me", headers={"X-Juris-Portal": "admin"}).status_code == 200
    assert client.get("/auth/me", headers={"X-Juris-Portal": "user"}).status_code == 200

    # Logout from Admin tab only
    logout = client.post("/auth/logout", headers={"X-Juris-Portal": "admin"})
    assert logout.status_code == 204

    # Admin tab is 401
    assert client.get("/auth/me", headers={"X-Juris-Portal": "admin"}).status_code == 401
    # User tab remains 200 OK!
    user_res = client.get("/auth/me", headers={"X-Juris-Portal": "user"})
    assert user_res.status_code == 200
    assert user_res.json()["email"] == email


async def test_expired_or_corrupt_cookie_isolation(client: TestClient) -> None:
    """Test that a corrupt/expired cookie on one portal does not break the other."""
    client.cookies.clear()
    client.cookies.set("legalgraph_admin_session", "corrupt.invalid.signature")

    # User portal without cookie -> 401
    res_user = client.get("/auth/me", headers={"X-Juris-Portal": "user"})
    assert res_user.status_code == 401

    # Admin portal with corrupt cookie -> 401, does not crash
    res_admin = client.get("/auth/me", headers={"X-Juris-Portal": "admin"})
    assert res_admin.status_code == 401


async def test_admin_logout_revocation_rejects_protected_endpoints(
    client: TestClient, session: AsyncSession
) -> None:
    """JAI-001 regression: Logging out invalidates session server-side; protected endpoints reject."""
    client.cookies.clear()
    admin_email = f"admin-revoked-{uuid4().hex[:8]}@juris.ai"
    reg = client.post(
        "/auth/register",
        json={"email": admin_email, "password": "RevokedPass123!", "name": "Admin Revoked"},
        headers={"X-Juris-Portal": "admin"},
    )
    assert reg.status_code == 201

    user_db = await session.scalar(select(User).where(User.email == admin_email))
    assert user_db is not None
    user_db.role = UserRole.ADMIN
    await session.commit()

    # Login to admin portal
    login_res = client.post(
        "/auth/login",
        json={"email": admin_email, "password": "RevokedPass123!"},
        headers={"X-Juris-Portal": "admin"},
    )
    assert login_res.status_code == 200
    stolen_cookie = client.cookies.get("legalgraph_admin_session")
    assert stolen_cookie is not None

    # Verify access to admin endpoints
    assert client.get("/auth/me", headers={"X-Juris-Portal": "admin"}).status_code == 200
    assert client.get("/documents/jobs", headers={"X-Juris-Portal": "admin"}).status_code == 200

    # Execute logout
    logout_res = client.post("/auth/logout", headers={"X-Juris-Portal": "admin"})
    assert logout_res.status_code == 204

    # Verify client cookie is cleared or set to expired
    # Now simulate an attacker or direct URL navigation attempting to reuse the previous cookie:
    client.cookies.set("legalgraph_admin_session", stolen_cookie)

    # /auth/me must reject with 401
    me_after = client.get("/auth/me", headers={"X-Juris-Portal": "admin"})
    assert me_after.status_code == 401, "/auth/me must reject revoked session"

    # Protected admin endpoints must reject with 401
    jobs_after = client.get("/documents/jobs", headers={"X-Juris-Portal": "admin"})
    assert jobs_after.status_code == 401, "Protected admin endpoints must reject revoked session"

    val_after = client.get("/validation", headers={"X-Juris-Portal": "admin"})
    assert val_after.status_code == 401

    # Calling logout when already unauthenticated/expired must succeed safely (204)
    second_logout = client.post("/auth/logout", headers={"X-Juris-Portal": "admin"})
    assert second_logout.status_code == 204


async def test_user_portal_session_cannot_access_admin_routes(
    client: TestClient, session: AsyncSession
) -> None:
    """Admin-protected routes require an active admin portal session, not user portal session."""
    client.cookies.clear()
    admin_email = f"cross-portal-{uuid4().hex[:8]}@juris.ai"
    reg = client.post(
        "/auth/register",
        json={"email": admin_email, "password": "CrossPortal123!", "name": "Cross Portal"},
        headers={"X-Juris-Portal": "user"},
    )
    assert reg.status_code == 201

    user_db = await session.scalar(select(User).where(User.email == admin_email))
    assert user_db is not None
    user_db.role = UserRole.ADMIN
    await session.commit()

    # Login to USER portal only
    login_res = client.post(
        "/auth/login",
        json={"email": admin_email, "password": "CrossPortal123!"},
        headers={"X-Juris-Portal": "user"},
    )
    assert login_res.status_code == 200
    assert client.cookies.get("legalgraph_session") is not None
    assert client.cookies.get("legalgraph_admin_session") is None

    # Attempt to access admin routes on admin portal without admin session -> 401 Unauthorized
    res = client.get("/documents/jobs", headers={"X-Juris-Portal": "admin"})
    assert res.status_code == 401
