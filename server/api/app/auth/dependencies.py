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
    user = await session.get(User, user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled")
    return user


require_authenticated_user = get_current_user


def require_role(*allowed_roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Return a dependency enforcing one or more application roles."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return dependency


require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_role(UserRole.SUPER_ADMIN)
