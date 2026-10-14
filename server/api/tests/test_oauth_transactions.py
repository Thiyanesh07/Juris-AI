from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request

from app.auth.google import (
    OAUTH_SESSION_BINDING_KEY,
    _digest,
    consume_oauth_state,
    validate_redirect_uri,
)
from app.core.config import Settings


def _request(binding: str) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/google/callback",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 50000),
            "scheme": "http",
        }
    )
    request.scope["session"] = {OAUTH_SESSION_BINDING_KEY: binding}
    return request


class _AtomicTransactionStore:
    def __init__(self, state: str, binding: str) -> None:
        self.state_digest = _digest(state)
        self.binding_digest = _digest(binding)
        self.consumed = False
        self.commits = 0
        self.statements: list[object] = []

    async def execute(self, statement: object) -> SimpleNamespace:
        self.statements.append(statement)
        if self.consumed:
            return SimpleNamespace(one_or_none=lambda: None)
        self.consumed = True
        return SimpleNamespace(
            one_or_none=lambda: (
                "signin",
                "/home",
                "http://localhost:5173/auth/google/callback",
            )
        )

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.consumed = False


@pytest.mark.asyncio
async def test_oauth_transaction_is_consumed_once() -> None:
    settings = Settings(
        session_secret="test-secret-key-32-chars-minimum-len",
        google_redirect_uri="http://localhost:5173/auth/google/callback",
    )
    binding = "browser-binding"
    store = _AtomicTransactionStore("issued-state", binding)

    first = await consume_oauth_state(
        _request(binding),
        store,  # type: ignore[arg-type]
        settings,
        "issued-state",
        "http://localhost:5173/auth/google/callback",
    )
    assert first[0] == "signin"
    assert store.commits == 1

    with pytest.raises(HTTPException) as replay:
        await consume_oauth_state(
            _request(binding),
            store,  # type: ignore[arg-type]
            settings,
            "issued-state",
            "http://localhost:5173/auth/google/callback",
        )
    assert replay.value.status_code == 400


@pytest.mark.asyncio
async def test_missing_or_expired_transactions_are_rejected() -> None:
    settings = Settings(
        session_secret="test-secret-key-32-chars-minimum-len",
        google_redirect_uri="http://localhost:5173/auth/google/callback",
    )
    binding = "browser-binding"
    store = _AtomicTransactionStore("issued-state", binding)

    with pytest.raises(HTTPException) as missing:
        await consume_oauth_state(
            _request(binding),
            store,  # type: ignore[arg-type]
            settings,
            None,
            "http://localhost:5173/auth/google/callback",
        )
    assert missing.value.status_code == 400

    store.consumed = True
    with pytest.raises(HTTPException) as expired:
        await consume_oauth_state(
            _request(binding),
            store,  # type: ignore[arg-type]
            settings,
            "expired-state",
            "http://localhost:5173/auth/google/callback",
        )
    assert expired.value.status_code == 400
    assert "expires_at" in str(store.statements[-1])


def test_redirect_uri_must_be_explicitly_configured_and_https_in_production() -> None:
    settings = Settings(
        app_env="production",
        session_secret="production-secret-key-that-is-long-enough",
        session_cookie_secure=True,
        google_redirect_uri="https://api.example.test/auth/google/callback",
    )
    assert (
        validate_redirect_uri(settings, "https://api.example.test/auth/google/callback")
        == "https://api.example.test/auth/google/callback"
    )
    with pytest.raises(HTTPException):
        validate_redirect_uri(settings, "https://attacker.example/callback")
    with pytest.raises(HTTPException):
        validate_redirect_uri(settings, "http://api.example.test/auth/google/callback")


def test_user_and_admin_redirect_uris_are_exactly_allowlisted() -> None:
    settings = Settings(
        google_redirect_uri="https://user.example/auth/google/callback",
        google_allowed_redirect_uris="https://admin.example/admin/auth/google/callback",
    )
    assert (
        validate_redirect_uri(settings, "https://user.example/auth/google/callback")
        == "https://user.example/auth/google/callback"
    )
    assert (
        validate_redirect_uri(settings, "https://admin.example/admin/auth/google/callback")
        == "https://admin.example/admin/auth/google/callback"
    )
    for invalid in (
        "https://user.example/auth/google/callback/",
        "https://other.example/auth/google/callback",
        "https://admin.example/auth/google/callback",
    ):
        with pytest.raises(HTTPException):
            validate_redirect_uri(settings, invalid)


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://*.example/auth/google/callback",
        "not-a-url",
        "https://portal.example/auth/google/callback?next=/home",
        "https://portal.example/other/callback",
    ],
)
def test_settings_reject_malformed_or_wildcard_redirect_uris(redirect_uri: str) -> None:
    with pytest.raises(ValueError, match="OAuth redirect URIs"):
        Settings(
            google_redirect_uri=redirect_uri,
            session_secret="test-session-secret-not-for-production",
        )


def test_production_settings_reject_http_redirect_uri() -> None:
    with pytest.raises(ValueError, match="must use HTTPS"):
        Settings(
            app_env="production",
            session_secret="a" * 64,
            session_cookie_secure=True,
            google_redirect_uri="http://portal.example/auth/google/callback",
        )
