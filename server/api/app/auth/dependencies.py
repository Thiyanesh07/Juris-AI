"""Reusable authenticated-user and role dependencies."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import User, UserRole


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    """Load the user identified by the signed server session cookie."""
    raw_user_id = request.session.get("user_id")
    if not isinstance(raw_user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        user_id = UUID(raw_user_id)
    except ValueError as exc:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from exc
    raw_session_version = request.session.get("session_version")
    if isinstance(raw_session_version, bool) or not isinstance(raw_session_version, int):
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user = await session.get(User, user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled")
    portal = request.session.get("portal") or request.scope.get("portal") or "user"
    expected_version = (user.session_version >> 16) & 0xFFFF if portal == "admin" else (user.session_version & 0xFFFF)
    if portal == "admin":
        if raw_session_version != expected_version:
            request.scope["session_cleared"] = True
            request.session.clear()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    else:
        if raw_session_version != expected_version and raw_session_version != user.session_version:
            request.scope["session_cleared"] = True
            request.session.clear()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    return user


require_authenticated_user = get_current_user


def require_role(*allowed_roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Return a dependency enforcing one or more application roles."""

    async def dependency(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        # Protect admin endpoints from being accessed using non-admin portal sessions
        if UserRole.ADMIN in allowed_roles or UserRole.SUPER_ADMIN in allowed_roles:
            request_portal = request.scope.get("portal")
            session_portal = request.session.get("portal")
            if request_portal == "admin" and session_portal is not None and session_portal != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin actions require an active administrator session",
                )
        return user

    return dependency


require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_role(UserRole.SUPER_ADMIN)
