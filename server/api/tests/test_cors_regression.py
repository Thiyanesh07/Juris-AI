"""Regression tests for production CORS and preflight OPTIONS handling."""

import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize("origin", [
    "https://juris-ai-admin.vercel.app",
    "https://juris-ai-user.vercel.app",
    "https://juris-ai-landing-ten.vercel.app",
])
def test_preflight_options_response(origin: str):
    """Verify that OPTIONS preflight requests return valid headers without illegal characters."""
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "content-type, authorization, accept",
    }
    response = client.options("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    
    allow_headers = response.headers.get("access-control-allow-headers", "")
    assert "multipart/form-data" not in allow_headers
    assert "/" not in allow_headers


@pytest.mark.parametrize("origin", [
    "https://juris-ai-admin.vercel.app",
    "https://juris-ai-user.vercel.app",
])
def test_auth_me_unauthenticated_cors(origin: str):
    """Verify GET /auth/me unauthenticated request returns 401 with proper CORS header."""
    headers = {"Origin": origin}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
