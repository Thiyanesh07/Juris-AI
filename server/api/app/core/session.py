"""Portal-isolated session middleware for Juris AI.

Eliminates cross-portal cookie collisions by isolating session state into:
  - 'legalgraph_admin_session' for the Admin Portal
  - 'legalgraph_session' for the User Portal

Maintains complete backwards compatibility, HttpOnly/SameSite/Secure attributes,
session versioning, and cross-user isolation.
"""

from __future__ import annotations

import json
from base64 import b64decode, b64encode
from typing import Literal

from itsdangerous import BadSignature, TimestampSigner
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ADMIN_COOKIE_NAME = "legalgraph_admin_session"
USER_COOKIE_NAME = "legalgraph_session"


def get_request_portal(connection: HTTPConnection) -> Literal["admin", "user"]:
    """Determine whether an HTTP connection is directed to the admin or user portal."""
    # 1. Explicit portal header
    portal_header = connection.headers.get("x-juris-portal", "").strip().lower()
    if portal_header == "admin":
        return "admin"
    if portal_header == "user":
        return "user"

    # 2. Check cookies present on connection
    cookies = connection.cookies
    if ADMIN_COOKIE_NAME in cookies and USER_COOKIE_NAME not in cookies:
        return "admin"
    if USER_COOKIE_NAME in cookies and ADMIN_COOKIE_NAME not in cookies:
        return "user"

    # 3. Origin header check
    origin = connection.headers.get("origin", "").lower()
    if "juris-ai-admin" in origin or ":3001" in origin:
        return "admin"
    if "juris-ai-user" in origin or ":3000" in origin:
        return "user"

    # 4. Referer header check
    referer = connection.headers.get("referer", "").lower()
    if "juris-ai-admin" in referer or ":3001" in referer:
        return "admin"
    if "juris-ai-user" in referer or ":3000" in referer:
        return "user"

    # 5. OAuth query parameters (redirect_uri or return_to)
    query_str = connection.scope.get("query_string", b"").decode("latin-1").lower()
    if "redirect_uri" in query_str and "admin" in query_str:
        return "admin"
    if "return_to" in query_str and "admin" in query_str:
        return "admin"

    # Default to user portal
    return "user"


def get_portal_session_version(user_version: int, portal: str) -> int:
    """Return the 16-bit partition of session_version for the given portal."""
    if portal == "admin":
        return (user_version >> 16) & 0xFFFF
    return user_version & 0xFFFF


def increment_portal_session_version(user_version: int, portal: str) -> int:
    """Increment the 16-bit partition for the given portal while preserving the other."""
    admin_ver = (user_version >> 16) & 0xFFFF
    user_ver = user_version & 0xFFFF
    if portal == "admin":
        admin_ver = (admin_ver + 1) & 0xFFFF
        if admin_ver == 0:
            admin_ver = 1
    else:
        user_ver = (user_ver + 1) & 0xFFFF
        if user_ver == 0:
            user_ver = 1
    return (admin_ver << 16) | user_ver


class PortalSessionMiddleware:
    """Session middleware that partitions session cookies between admin and user portals."""

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str | bytes,
        admin_cookie: str = ADMIN_COOKIE_NAME,
        user_cookie: str = USER_COOKIE_NAME,
        max_age: int | None = 14 * 24 * 60 * 60,
        path: str = "/",
        same_site: str = "lax",
        https_only: bool = False,
        domain: str | None = None,
    ) -> None:
        self.app = app
        self.signer = TimestampSigner(str(secret_key))
        self.admin_cookie = admin_cookie
        self.user_cookie = user_cookie
        self.max_age = max_age
        self.path = path
        self.security_flags = f"httponly; samesite={same_site}"
        if https_only:
            self.security_flags += "; secure"
        if domain is not None:
            self.security_flags += f"; domain={domain}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        portal = get_request_portal(connection)
        cookie_name = self.admin_cookie if portal == "admin" else self.user_cookie

        scope["portal"] = portal
        scope["session_cookie_name"] = cookie_name

        had_cookie = cookie_name in connection.cookies
        initial_session_was_empty = True

        if had_cookie:
            data = connection.cookies[cookie_name].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = json.loads(b64decode(data))
                initial_session_was_empty = False
            except (BadSignature, Exception):
                scope["session"] = {}
        else:
            scope["session"] = {}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                target_cookie = scope.get("session_cookie_name", cookie_name)
                headers = MutableHeaders(scope=message)

                if scope.get("session"):
                    # Persist modified/active session
                    data = b64encode(json.dumps(scope["session"]).encode("utf-8"))
                    signed_data = self.signer.sign(data).decode("utf-8")
                    max_age_str = f"max-age={self.max_age}; " if self.max_age else ""
                    header_value = (
                        f"{target_cookie}={signed_data}; path={self.path}; "
                        f"{max_age_str}{self.security_flags}"
                    )
                    headers.append("set-cookie", header_value)
                elif not initial_session_was_empty or had_cookie or scope.get("session_cleared"):
                    # Clear revoked/logged-out session with both max-age=0 and past expires
                    header_value = (
                        f"{target_cookie}=null; path={self.path}; "
                        f"max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; {self.security_flags}"
                    )
                    headers.append("set-cookie", header_value)

            await send(message)

        await self.app(scope, receive, send_wrapper)
