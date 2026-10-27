"""Google OAuth code-exchange boundary and identity resolution."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import OAuthTransaction, User, UserRole

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
OAUTH_SESSION_BINDING_KEY = "oauth_session_binding"
OAUTH_STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str | None
    image_url: str | None


def validate_return_path(value: str | None) -> str | None:
    """Allow only a local application path for post-authentication navigation."""
    if not value:
        return None
    candidate = value.strip()
    if len(candidate) > 2048 or not candidate.startswith("/") or candidate.startswith("//"):
        return None
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    return candidate


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def allowed_redirect_uris(settings: Settings) -> frozenset[str]:
    values: set[str] = set()
    if settings.google_redirect_uri and settings.google_redirect_uri.strip():
        values.add(settings.google_redirect_uri.strip())
    for part in settings.google_allowed_redirect_uris.split(","):
        candidate = part.strip()
        if candidate:
            values.add(candidate)
            # Accept admin portal callback when configured with either prefix
            if "juris-ai-admin" in candidate and candidate.endswith("/auth/google/callback"):
                values.add(candidate.replace("/auth/google/callback", "/admin/auth/google/callback"))
            elif "juris-ai-admin" in candidate and candidate.endswith("/admin/auth/google/callback"):
                values.add(candidate.replace("/admin/auth/google/callback", "/auth/google/callback"))
            elif ":3001" in candidate and candidate.endswith("/auth/google/callback"):
                values.add(candidate.replace("/auth/google/callback", "/admin/auth/google/callback"))

    # Include known first-party portal callbacks according to environment
    if settings.app_env != "production":
        values.add("http://localhost:3001/admin/auth/google/callback")
        values.add("http://localhost:3002/auth/google/callback")
    else:
        values.add("https://juris-ai-admin.vercel.app/admin/auth/google/callback")
        values.add("https://juris-ai-user.vercel.app/auth/google/callback")

    return frozenset(values)


def validate_redirect_uri(settings: Settings, redirect_uri: str | None) -> str:
    """Require an exact, explicitly configured OAuth callback URI."""
    candidate = redirect_uri or settings.google_redirect_uri
    if candidate not in allowed_redirect_uris(settings):
        raise HTTPException(status_code=400, detail="Invalid OAuth redirect URI")
    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
        or (settings.app_env == "production" and parsed.scheme != "https")
    ):
        raise HTTPException(status_code=400, detail="Invalid OAuth redirect URI")
    return candidate


async def begin_oauth_state(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    intent: str,
    return_to: str | None,
    redirect_uri: str | None,
) -> str:
    """Create a server-side, one-time OAuth transaction."""
    state = secrets.token_urlsafe(32)
    binding = secrets.token_urlsafe(32)
    request.session[OAUTH_SESSION_BINDING_KEY] = binding
    validated_return_to = validate_return_path(return_to)
    effective_redirect_uri = validate_redirect_uri(settings, redirect_uri)
    session.add(
        OAuthTransaction(
            state_digest=_digest(state),
            session_binding=_digest(binding),
            intent=intent,
            return_to=validated_return_to,
            redirect_uri=effective_redirect_uri,
            expires_at=datetime.now(UTC)
            + timedelta(seconds=OAUTH_STATE_TTL_SECONDS),
        )
    )
    await session.commit()
    return state


async def consume_oauth_state(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    received_state: str | None,
    redirect_uri: str | None,
) -> tuple[str, str | None, str]:
    """Atomically consume a matching, unexpired OAuth transaction."""
    if not isinstance(received_state, str) or not received_state or len(received_state) > 256:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    binding = request.session.get(OAUTH_SESSION_BINDING_KEY)
    if not isinstance(binding, str):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    effective_redirect_uri = validate_redirect_uri(settings, redirect_uri)
    statement = (
        delete(OAuthTransaction)
        .where(
            OAuthTransaction.state_digest == _digest(received_state),
            OAuthTransaction.session_binding == _digest(binding),
            OAuthTransaction.expires_at > datetime.now(UTC),
            OAuthTransaction.consumed_at.is_(None),
            OAuthTransaction.redirect_uri == effective_redirect_uri,
        )
        .returning(
            OAuthTransaction.intent,
            OAuthTransaction.return_to,
            OAuthTransaction.redirect_uri,
        )
    )
    result = await session.execute(statement)
    transaction = result.one_or_none()
    if transaction is None:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    await session.commit()
    request.session.pop(OAUTH_SESSION_BINDING_KEY, None)
    intent, return_to, effective_redirect_uri = transaction
    return intent, return_to, effective_redirect_uri


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
    effective_redirect = validate_redirect_uri(settings, redirect_uri)
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
    effective_redirect = validate_redirect_uri(settings, redirect_uri)
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
        user.last_login_at = datetime.now(UTC)
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
            last_login_at=datetime.now(UTC),
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
                last_login_at=datetime.now(UTC),
            )
            session.add(user)
        else:
            user.google_subject = identity.subject
            if identity.name:
                user.name = identity.name
            if identity.image_url:
                user.image_url = identity.image_url
            user.last_login_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(user)
    return user
