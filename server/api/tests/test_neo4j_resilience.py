"""Tests for Neo4j client resilience, lifecycle, error classification, and health reporting.

Ensures that Neo4j failures are classified properly, driver resources are cleanly closed,
health checks distinguish empty graphs from unavailable databases, and dense retrieval fallback
operates safely without depending on live cloud Neo4j Aura.
"""

from __future__ import annotations

import asyncio
from typing import Any
import pytest

from app.core.config import Settings
from app.graph.client import (
    GraphAuthenticationError,
    GraphConnectionError,
    GraphError,
    Neo4jClient,
)
from tests.fake_neo4j import FakeNeo4jClient, InMemoryGraph


@pytest.mark.asyncio
async def test_driver_lifecycle_clean_shutdown() -> None:
    """Verify driver creation, close method, and async context manager."""
    client = Neo4jClient(Settings(session_secret="test", neo4j_uri="bolt://127.0.0.1:9999"))
    assert client._driver is None

    # Closing before connection should be a clean no-op
    await client.close()
    assert client._driver is None

    # Context manager protocol
    async with Neo4jClient(Settings(session_secret="test", neo4j_uri="bolt://127.0.0.1:9999")) as ctx_client:
        assert ctx_client._driver is None
    assert ctx_client._driver is None


def test_error_classification() -> None:
    """Verify error classification between connection failure, auth failure, and generic error."""
    client = Neo4jClient(Settings(session_secret="test"))

    # Connection failure
    conn_exc = ConnectionRefusedError("[WinError 10061] No connection could be made")
    classified_conn = client._classify_error(conn_exc)
    assert isinstance(classified_conn, GraphConnectionError)
    assert isinstance(classified_conn, GraphError)
    assert "connection failed" in str(classified_conn).lower()

    # Timeout
    timeout_exc = TimeoutError("Connection acquisition timed out after 5.0s")
    classified_timeout = client._classify_error(timeout_exc)
    assert isinstance(classified_timeout, GraphConnectionError)

    # Auth failure
    class AuthError(Exception):
        pass

    auth_exc = AuthError("The client is unauthorized due to authentication failure")
    classified_auth = client._classify_error(auth_exc)
    assert isinstance(classified_auth, GraphAuthenticationError)
    assert "authentication failed" in str(classified_auth).lower()

    # Generic graph error
    gen_exc = ValueError("Invalid Cypher syntax")
    classified_gen = client._classify_error(gen_exc)
    assert type(classified_gen) is GraphError


@pytest.mark.asyncio
async def test_health_reporting_distinguishes_empty_from_populated() -> None:
    """Health response must report is_empty: True on an empty graph and is_empty: False on populated graph."""
    fake_client = FakeNeo4jClient()

    # Empty graph
    health_empty = await fake_client.health()
    assert health_empty["status"] == "ok"
    assert health_empty["is_empty"] is True
    assert health_empty["node_count"] == 0

    # Populated graph
    fake_client.graph.merge_node("Document", {"id": "doc-1", "title": "Test Act", "document_type": "act"})
    health_pop = await fake_client.health()
    assert health_pop["status"] == "ok"
    assert health_pop["is_empty"] is False
    assert health_pop["node_count"] == 1


@pytest.mark.asyncio
async def test_client_timeout_when_neo4j_unreachable() -> None:
    """Client must fail boundedly within seconds rather than hanging indefinitely when host is unreachable."""
    # Using non-routable documentation IP (TEST-NET-1: 192.0.2.1)
    unreachable_settings = Settings(
        session_secret="test",
        neo4j_uri="bolt://192.0.2.1:7687",
        neo4j_username="neo4j",
        neo4j_password="password",
    )
    client = Neo4jClient(unreachable_settings)

    start = asyncio.get_event_loop().time()
    with pytest.raises(GraphError):
        # Bound with an outer timeout as safety guarantee
        await asyncio.wait_for(client.verify_connectivity(), timeout=8.0)
    elapsed = asyncio.get_event_loop().time() - start

    # Should have timed out quickly via the 5.0s connection_timeout
    assert elapsed < 7.5
    await client.close()


@pytest.mark.asyncio
async def test_health_check_raises_graph_error_when_offline() -> None:
    """Health check on offline instance raises classified GraphError."""
    # Pointing to loopback closed port
    closed_settings = Settings(
        session_secret="test",
        neo4j_uri="bolt://127.0.0.1:59999",
        neo4j_username="neo4j",
        neo4j_password="password",
    )
    client = Neo4jClient(closed_settings)
    with pytest.raises(GraphConnectionError):
        await client.health()
    await client.close()
