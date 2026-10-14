"""Browser authentication routes (email/password sessions & Google OAuth)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.google import (
    begin_oauth_state,
    consume_oauth_state,
    exchange_code_for_identity,
    find_or_create_user,
    google_login_url,
)
from app.auth.password import hash_password, verify_password
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models import User, UserRole
from app.schemas.auth import CurrentUserResponse, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(request: Request, user: User) -> None:
    request.session.clear()
    request.session["user_id"] = str(user.id)
    request.session["session_version"] = user.session_version


@router.get("/google/login", response_model=None)
async def google_login(
    request: Request,
    intent: str = Query("signin", description="OAuth intent: signin or signup"),
    state: str = Query("", description="Legacy return path; not used as security state"),
    redirect_uri: str | None = Query(None, description="Custom OAuth redirect URI"),
    return_to: str | None = Query(None, description="Legacy parameter for return path"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse | dict[str, str]:
    """Initiate Google OAuth authentication redirect with intent support."""
    validated_intent = intent if intent in ("signin", "signup") else "signin"
    effective_state = await begin_oauth_state(
        request,
        session,
        settings,
        validated_intent,
        return_to or state,
        redirect_uri,
    )

    auth_url = google_login_url(settings, state=effective_state, redirect_uri=redirect_uri)

    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return {"url": auth_url}

    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback", response_model=CurrentUserResponse)
async def google_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: str | None = Query(None, description="Opaque OAuth state"),
    intent: str | None = Query(None, description="OAuth intent override"),
    redirect_uri: str | None = Query(None, description="Custom OAuth redirect URI"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Exchange authorization code for verified identity and resolve user according to intent."""
    resolved_intent, _return_to, effective_redirect_uri = await consume_oauth_state(
        request,
        session,
        settings,
        state,
        redirect_uri,
    )

    identity = await exchange_code_for_identity(
        code,
        settings,
        redirect_uri=effective_redirect_uri,
    )
    user = await find_or_create_user(session, identity, intent=resolved_intent)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    _start_session(request, user)
    return user


@router.post("/register", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    email = body.email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=email,
        name=body.name.strip() if body.name and body.name.strip() else None,
        password_hash=hash_password(body.password),
        role=UserRole.USER,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    _start_session(request, user)
    return user


@router.post("/login", response_model=CurrentUserResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    email = body.email.lower()
    user = await session.scalar(select(User).where(User.email == email))
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    _start_session(request, user)
    return user


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    user.session_version += 1
    await session.commit()
    request.session.clear()
