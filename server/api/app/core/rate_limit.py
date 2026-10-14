"""Small fixed-window request limiter for abuse-sensitive API endpoints.

The limiter is intentionally dependency-free. Its state is process-local, so
deployments with multiple workers or instances must add an equivalent
edge/shared-store limit for a global quota.
"""

from __future__ import annotations

import ipaddress
import math
import threading
import time
from dataclasses import dataclass
from typing import Final

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import Settings

_AUTH_PATHS: Final = {
    ("/auth/login", "POST"),
    ("/auth/register", "POST"),
    ("/auth/google/login", "GET"),
    ("/auth/google/callback", "GET"),
}
_LIMITED_PATHS: Final = {
    "/qa/ask": "qa",
    "/documents/upload": "upload",
}


@dataclass
class _Window:
    started_at: float
    count: int = 0


class InMemoryRateLimiter:
    """Thread-safe fixed-window counter used by the middleware."""

    def __init__(self, max_entries: int = 10_000) -> None:
        self._windows: dict[tuple[str, str], _Window] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def allow(self, key: tuple[str, str], limit: int, window_seconds: int) -> int | None:
        """Return retry seconds when blocked, otherwise record and allow a request."""
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now, window_seconds)
            window = self._windows.get(key)
            if window is None or now - window.started_at >= window_seconds:
                if len(self._windows) >= self._max_entries:
                    self._evict_oldest()
                self._windows[key] = _Window(started_at=now, count=1)
                return None
            if window.count >= limit:
                return max(1, math.ceil(window_seconds - (now - window.started_at)))
            window.count += 1
            return None

    def _evict_expired(self, now: float, window_seconds: int) -> None:
        expired = [
            key
            for key, window in self._windows.items()
            if now - window.started_at >= window_seconds
        ]
        for key in expired:
            self._windows.pop(key, None)

    def _evict_oldest(self) -> None:
        oldest_key = min(self._windows, key=lambda key: self._windows[key].started_at)
        self._windows.pop(oldest_key, None)

    def clear(self) -> None:
        """Clear all counters, primarily for application lifecycle and tests."""
        with self._lock:
            self._windows.clear()


def _normalise_path(path: str) -> str:
    if path == "/api/v1":
        return "/"
    if path.startswith("/api/v1/"):
        return path[len("/api/v1") :]
    return path


def _trusted_networks(
    settings: Settings,
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for value in settings.trusted_proxy_ips.split(","):
        value = value.strip()
        if value:
            networks.append(ipaddress.ip_network(value, strict=False))
    return tuple(networks)


def client_identity(request: Request, settings: Settings) -> str:
    """Return a client identity without trusting arbitrary forwarded headers."""
    peer = request.client.host if request.client else "unknown"
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer

    if any(peer_ip in network for network in _trusted_networks(settings)):
        forwarded = request.headers.get("x-forwarded-for", "")
        for candidate in reversed([part.strip() for part in forwarded.split(",") if part.strip()]):
            try:
                candidate_ip = ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if not any(candidate_ip in network for network in _trusted_networks(settings)):
                return candidate
    return peer


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply configurable limits to authentication, QA, and upload requests."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.limiter = InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = _normalise_path(request.url.path)
        method = request.method.upper()
        category = dict(_LIMITED_PATHS).get(path)
        if category is None and (path, method) in _AUTH_PATHS:
            category = "auth"
        if category is None or not self.settings.rate_limit_enabled:
            return await call_next(request)

        limit = {
            "auth": self.settings.rate_limit_auth_requests,
            "qa": self.settings.rate_limit_qa_requests,
            "upload": self.settings.rate_limit_upload_requests,
        }[category]
        ip_key = ("ip", client_identity(request, self.settings))
        keys = [ip_key]
        if category in {"qa", "upload"}:
            session_data = request.scope.get("session", {})
            user_id = session_data.get("user_id") if isinstance(session_data, dict) else None
            if isinstance(user_id, str) and user_id:
                keys.append(("user", user_id))

        retry_after = max(
            (
                retry
                for key in keys
                if (retry := self.limiter.allow(
                    (category, f"{key[0]}:{key[1]}"),
                    limit,
                    self.settings.rate_limit_window_seconds,
                ))
                is not None
            ),
            default=None,
        )
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
