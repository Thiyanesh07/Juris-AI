"""Admin User and Administrator Management API Routes (Phase 16).

Provides server-side RBAC enforcement for managing platform users and administrators.
SUPER_ADMINs can provision admins and change roles. Ordinary ADMINs cannot modify SUPER_ADMINs.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_super_admin
from app.auth.password import hash_password
from app.db.session import get_session
from app.models import User, UserRole
from app.schemas.admin_user import (
    AdminProvisionRequest,
    PaginatedUsersResponse,
    UserProfileResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.audit import log_audit_event

router = APIRouter(tags=["users_admin"])


@router.get("/users/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    """Return profile for the currently authenticated user."""
    return current_user


@router.get("/admin/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter by name or email"),
    role: str | None = Query(None, description="Filter by user role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedUsersResponse:
    """List non-admin/platform users with search, filtering, and pagination."""
    query = select(User)
    count_query = select(func.count(User.id))

    filters = []
    if search:
        s = f"%{search.strip().lower()}%"
        filters.append((func.lower(User.email).like(s)) | (func.lower(User.name).like(s)))
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    users = (await session.scalars(query.order_by(User.created_at.desc()).offset(offset).limit(page_size))).all()

    return PaginatedUsersResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Retrieve details for a specific user."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Update user attributes (name, role, active status).

    - Only SUPER_ADMIN can assign ADMIN/SUPER_ADMIN roles.
    - SUPER_ADMIN cannot be disabled or demoted by non-SUPER_ADMIN.
    """
    target_user = await session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before_state = {
        "name": target_user.name,
        "role": target_user.role,
        "is_active": target_user.is_active,
    }

    # Protection: Non-SUPER_ADMIN cannot modify a SUPER_ADMIN account
    if target_user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify a Super Administrator account.",
        )

    # Protection: Cannot disable/demote SUPER_ADMIN
    if target_user.role == UserRole.SUPER_ADMIN:
        if body.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SUPER_ADMIN accounts cannot be disabled.",
            )
        if body.role and body.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SUPER_ADMIN accounts cannot be demoted.",
            )

    # Role escalation protection: Only SUPER_ADMIN can promote to ADMIN/SUPER_ADMIN
    if body.role:
        if body.role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value) and current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Administrators can promote users to administrative roles.",
            )
        target_user.role = UserRole(body.role)

    if body.name is not None:
        target_user.name = body.name.strip()
    if body.is_active is not None:
        target_user.is_active = body.is_active

    await session.commit()
    await session.refresh(target_user)

    after_state = {
        "name": target_user.name,
        "role": target_user.role,
        "is_active": target_user.is_active,
    }

    await log_audit_event(
        session,
        category="USER_MANAGEMENT",
        action="UPDATE",
        result="SUCCESS",
        severity="INFO",
        actor_id=current_user.id,
        target_resource=f"user:{target_user.id}",
        description=f"Updated user {target_user.email}",
        before_state=before_state,
        after_state=after_state,
    )

    return UserResponse.model_validate(target_user)


@router.get("/admin/admins", response_model=PaginatedUsersResponse)
async def list_administrators(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedUsersResponse:
    """List all platform administrators (ADMIN and SUPER_ADMIN roles)."""
    admin_roles = [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    query = select(User).where(User.role.in_(admin_roles))
    count_query = select(func.count(User.id)).where(User.role.in_(admin_roles))

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    admins = (await session.scalars(query.order_by(User.created_at.desc()).offset(offset).limit(page_size))).all()

    return PaginatedUsersResponse(
        items=[UserResponse.model_validate(a) for a in admins],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def provision_administrator(
    body: AdminProvisionRequest,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Provision a new administrator account (SUPER_ADMIN only)."""
    email = body.email.lower().strip()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    target_role = UserRole.ADMIN if body.role == "admin" else UserRole.SUPER_ADMIN
    new_admin = User(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role=target_role,
        is_active=True,
    )
    session.add(new_admin)
    await session.commit()
    await session.refresh(new_admin)

    await log_audit_event(
        session,
        category="ADMIN_MANAGEMENT",
        action="PROVISION",
        result="SUCCESS",
        severity="WARNING",
        actor_id=current_user.id,
        target_resource=f"user:{new_admin.id}",
        description=f"Provisioned new admin {new_admin.email} as {new_admin.role}",
        after_state={"email": new_admin.email, "role": new_admin.role, "is_active": True},
    )

    return UserResponse.model_validate(new_admin)
