"""Google OAuth code-exchange boundary and identity resolution."""

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import User, UserRole

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str | None
    image_url: str | None


def _oauth_not_configured_error(settings: Settings) -> HTTPException:
    missing: list[str] = []
    if not settings.google_client_id:
        missing.append("GOOGLE_CLIENT_ID")
    if not settings.google_client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")
    if not settings.google_redirect_uri:
        missing.append("GOOGLE_REDIRECT_URI")
    hint = (
        " Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env / .env.local, "
        "or place the Google Cloud OAuth client JSON at google-oauth-client.json "
        "in the project root."
    )
    return HTTPException(
        status_code=503,
        detail=f"Google OAuth is not configured (missing: {', '.join(missing)}).{hint}",
    )


def google_login_url(settings: Settings, state: str = "", redirect_uri: str | None = None) -> str:
    """Build the provider authorization URL without exposing a client secret."""
    effective_redirect = redirect_uri or settings.google_redirect_uri
    if not all((settings.google_client_id, effective_redirect)):
        raise _oauth_not_configured_error(settings)
    return str(
        httpx.URL(
            "https://accounts.google.com/o/oauth2/v2/auth",
            params={
                "client_id": settings.google_client_id,
                "redirect_uri": effective_redirect,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            },
        )
    )


async def exchange_code_for_identity(
    code: str,
    settings: Settings,
    redirect_uri: str | None = None,
) -> GoogleIdentity:
    """Exchange an authorization code and fetch verified Google userinfo over TLS."""
    effective_redirect = redirect_uri or settings.google_redirect_uri
    if not all(
        (settings.google_client_id, settings.google_client_secret, effective_redirect)
    ):
        raise _oauth_not_configured_error(settings)
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": effective_redirect,
                "grant_type": "authorization_code",
            },
        )
        if token_response.is_error:
            raise HTTPException(status_code=400, detail="Google authorization failed")
        access_token = token_response.json().get("access_token")
        if not isinstance(access_token, str):
            raise HTTPException(status_code=400, detail="Google authorization failed")
        info_response = await client.get(
            _USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        if info_response.is_error:
            raise HTTPException(status_code=400, detail="Google identity lookup failed")
    payload = info_response.json()
    subject, email = payload.get("sub"), payload.get("email")
    if (
        not isinstance(subject, str)
        or not isinstance(email, str)
        or payload.get("email_verified") is not True
    ):
        raise HTTPException(
            status_code=400, detail="Google did not return a verified email identity"
        )
    return GoogleIdentity(
        subject=subject,
        email=email.lower(),
        name=payload.get("name") if isinstance(payload.get("name"), str) else None,
        image_url=payload.get("picture") if isinstance(payload.get("picture"), str) else None,
    )


async def find_or_create_user(
    session: AsyncSession,
    identity: GoogleIdentity,
    intent: str = "any",
) -> User:
    """Resolve a Google identity according to explicit intent (signin vs signup)."""
    user = await session.scalar(select(User).where(User.google_subject == identity.subject))
    if user is None:
        user = await session.scalar(select(User).where(User.email == identity.email))

    if intent == "signin":
        if user is None:
            raise HTTPException(
                status_code=404,
                detail="No Juris AI account found. Please sign up first.",
            )
        user.google_subject = identity.subject
        if identity.name:
            user.name = identity.name
        if identity.image_url:
            user.image_url = identity.image_url
        user.last_login_at = datetime.now(timezone.utc)
    elif intent == "signup":
        if user is not None:
            raise HTTPException(
                status_code=409,
                detail="This Google account already has a Juris AI account. Please sign in.",
            )
        user = User(
            email=identity.email,
            name=identity.name,
            image_url=identity.image_url,
            google_subject=identity.subject,
            role=UserRole.USER,
            is_active=True,
            last_login_at=datetime.now(timezone.utc),
        )
        session.add(user)
    else:
        # Legacy/admin fallback behavior ("any")
        if user is None:
            user = User(
                email=identity.email,
                name=identity.name,
                image_url=identity.image_url,
                google_subject=identity.subject,
                role=UserRole.USER,
                is_active=True,
                last_login_at=datetime.now(timezone.utc),
            )
            session.add(user)
        else:
            user.google_subject = identity.subject
            if identity.name:
                user.name = identity.name
            if identity.image_url:
                user.image_url = identity.image_url
            user.last_login_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(user)
    return user

