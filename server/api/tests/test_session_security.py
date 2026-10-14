import base64
import json
import time
from uuid import uuid4

import itsdangerous
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def test_production_rejects_development_secret() -> None:
    with pytest.raises(ValueError, match="development session secret"):
        Settings(
            app_env="production",
            session_secret="dev-secret-change-in-production-min-32-chars-long",
            session_cookie_secure=True,
        )


def test_missing_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(ValueError, match="app_env|APP_ENV"):
        Settings(
            _env_file=None,
            session_secret="test-session-secret-not-for-production",
        )


@pytest.mark.parametrize("app_env", ["development", "test", "Development", "TEST"])
def test_development_and_test_environment_values_are_valid(app_env: str) -> None:
    settings = Settings(
        app_env=app_env,
        session_secret="test-session-secret-not-for-production",
    )
    assert settings.app_env == app_env.lower()


@pytest.mark.parametrize("app_env", ["prod", "producton", "staging", ""])
def test_invalid_environment_values_are_rejected(app_env: str) -> None:
    with pytest.raises(ValueError, match="APP_ENV"):
        Settings(app_env=app_env, session_secret="test-session-secret-not-for-production")


@pytest.mark.parametrize("app_env", ["Production", "PRODUCTION"])
def test_production_environment_values_are_normalized(app_env: str) -> None:
    settings = Settings(
        app_env=app_env,
        session_secret="a" * 64,
        session_cookie_secure=True,
        google_redirect_uri="https://portal.example/auth/google/callback",
    )
    assert settings.app_env == "production"


def test_production_rejects_short_secret() -> None:
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            app_env="production",
            session_secret="too-short",
            session_cookie_secure=True,
        )


def test_production_requires_secure_session_cookie() -> None:
    with pytest.raises(ValueError, match="session_cookie_secure=True"):
        Settings(
            app_env="production",
            session_secret="a" * 64,
            session_cookie_secure=False,
        )


def test_production_accepts_strong_secret_and_secure_cookie() -> None:
    settings = Settings(
        app_env="production",
        session_secret="a" * 64,
        session_cookie_secure=True,
        session_max_age_seconds=3600,
        google_redirect_uri="https://portal.example/auth/google/callback",
    )
    assert settings.session_secret == "a" * 64
    assert settings.session_cookie_secure is True
    assert settings.session_max_age_seconds == 3600


def test_login_logout_and_cookie_attributes_use_real_app_session(
    client: TestClient,
) -> None:
    email = f"session-{uuid4().hex[:8]}@example.com"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Session User"},
    )
    assert register.status_code == 201
    set_cookie = register.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "max-age=604800" in set_cookie
    assert "secure" not in set_cookie

    assert client.get("/auth/me").status_code == 200
    logout = client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    assert logout.status_code == 204
    logout_cookie = logout.headers["set-cookie"].lower()
    assert "expires=thu, 01 jan 1970 00:00:00 gmt" in logout_cookie
    assert client.get("/auth/me").status_code == 401


def test_copied_cookie_is_rejected_after_logout_across_clients(
    client: TestClient,
) -> None:
    email = f"revoke-{uuid4().hex[:8]}@example.com"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Revoke User"},
    )
    assert register.status_code == 201
    copied_cookie = client.cookies.get("legalgraph_session")
    assert copied_cookie

    with TestClient(app) as replay_client:
        replay_client.cookies.set("legalgraph_session", copied_cookie)
        assert replay_client.get("/auth/me").status_code == 200

        logout = client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
        assert logout.status_code == 204

        replay = replay_client.get("/auth/me")
        assert replay.status_code == 401
        assert replay.json()["detail"] == "Session revoked"


def test_malformed_and_expired_session_cookies_are_rejected(client: TestClient) -> None:
    client.cookies.set("legalgraph_session", "not-a-signed-session")
    malformed = client.get("/auth/me")
    assert malformed.status_code == 401

    class ExpiredSigner(itsdangerous.TimestampSigner):
        def get_timestamp(self) -> int:
            return int(time.time()) - 3600

    payload = base64.b64encode(
        json.dumps({"user_id": str(uuid4()), "session_version": 0}).encode("utf-8")
    )
    expired_cookie = ExpiredSigner(get_settings().session_secret).sign(payload).decode("utf-8")
    client.cookies.set("legalgraph_session", expired_cookie)
    expired = client.get("/auth/me")
    assert expired.status_code == 401
