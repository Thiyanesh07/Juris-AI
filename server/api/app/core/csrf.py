"""Origin validation for cookie-authenticated state-changing requests."""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_AUTH_FLOW_PATHS = frozenset(
    {
        "/auth/login",
        "/auth/register",
        "/auth/google/callback",
    }
)
_DEFAULT_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:5173",
    "https://juris-ai-landing-ten.vercel.app",
    "https://juris-ai-user.vercel.app",
    "https://juris-ai-admin.vercel.app",
)


def _normalise_path(path: str) -> str:
    if path == "/api/v1":
        return "/"
    if path.startswith("/api/v1/"):
        return path[len("/api/v1") :]
    return path


def _origin_from_url(value: str, *, allow_path: bool = False) -> str | None:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password or (not allow_path and parsed.path not in {"", "/"}):
        return None
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def configured_origins(settings: object) -> frozenset[str]:
    """Return exact origins configured for browser frontends."""
    frontend_url = getattr(settings, "frontend_url", "")
    extra = getattr(settings, "extra_cors_origins", "")
    values = [
        *_DEFAULT_FRONTEND_ORIGINS,
        frontend_url,
        *(part.strip() for part in extra.split(",")),
    ]
    origins = {_origin_from_url(value.strip().strip("'\"")) for value in values if value}
    return frozenset(origin for origin in origins if origin is not None)


def request_origin(request: Request) -> str | None:
    """Extract one origin from Origin, or fall back to Referer."""
    origin = request.headers.get("origin")
    if origin is not None:
        return _origin_from_url(origin.strip())
    referer = request.headers.get("referer")
    if referer is not None:
        return _origin_from_url(referer.strip(), allow_path=True)
    return None


class CSRFMiddleware(BaseHTTPMiddleware):
    """Reject cross-site unsafe requests carrying an authenticated session."""

    def __init__(self, app: ASGIApp, settings: object) -> None:
        super().__init__(app)
        self.allowed_origins = configured_origins(settings)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = _normalise_path(request.url.path)
        session_data = request.scope.get("session", {})
        authenticated = (
            isinstance(session_data, dict)
            and isinstance(session_data.get("user_id"), str)
            and bool(session_data["user_id"])
        )
        if (
            authenticated
            and request.method.upper() not in _SAFE_METHODS
            and path not in _AUTH_FLOW_PATHS
        ):
            origin = request_origin(request)
            if origin is None or origin not in self.allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )
        return await call_next(request)
