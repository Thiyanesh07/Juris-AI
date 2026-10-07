"""Health endpoint contract tests (S01 liveness contract + G01 database part).

``/health`` keeps the S01 guarantees (HTTP 200, structured JSON, only health
endpoints exposed) and now additionally reports database connectivity.
"""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


def test_health_returns_structured_response_with_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["service"] == "juris-ai-backend" or body["service"] == "legalgraph-api"
    assert "status" in body
    assert "components" in body
    assert "database" in body["components"]
    assert body["components"]["database"]["status"] in ("ok", "CONNECTED")


def test_database_health_endpoint_reports_reachable(client: TestClient) -> None:
    response = client.get("/health/database")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "CONNECTED")


def test_health_reports_degraded_when_database_unreachable(client: TestClient) -> None:
    class FailingSession:
        async def execute(self, *args: object, **kwargs: object) -> None:
            raise OSError("database unavailable")

        async def rollback(self) -> None:
            return None

    async def failing_session() -> AsyncIterator[object]:
        yield FailingSession()

    app.dependency_overrides[get_session] = failing_session
    try:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["components"]["database"]["status"] == "unreachable"
        assert "database unavailable" in body["components"]["database"]["error"]

        response = client.get("/health/database")
        assert response.status_code == 503
        assert response.json()["status"] == "unavailable"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_only_expected_endpoints_are_exposed(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    expected_paths = {
        "/health",
        "/health/database",
        "/auth/register",
        "/auth/login",
        "/auth/me",
        "/auth/logout",
    }
    assert expected_paths.issubset(set(response.json()["paths"]))
