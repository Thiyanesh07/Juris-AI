import pytest
from typing import Any
from app.models import User, UserRole
from app.auth.password import hash_password
from app.api.routes.graph import get_graph_client
from app.main import app


class MockAsyncResult:
    def __init__(self, records):
        self._records = records

    def __aiter__(self):
        self._iter = iter(self._records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def single(self):
        return self._records[0] if self._records else None


class MockAsyncSession:
    def __init__(self, should_fail: bool = False):
        self._should_fail = should_fail

    async def __aenter__(self):
        if self._should_fail:
            raise RuntimeError("Connection refused by Neo4j cluster")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def run(self, query: str, **params: Any):
        if self._should_fail:
            raise RuntimeError("Query execution failed: Neo4j cluster is down")

        # Match search query
        if "label_type LIMIT $limit" in query:
            records = [
                {
                    "n": {
                        "id": "article:constitution_of_india:21",
                        "name": "Article 21 - Protection of Life and Personal Liberty",
                        "title": "Article 21",
                        "jurisdiction": "Union of India",
                    },
                    "label_type": "Article",
                },
                {
                    "n": {
                        "id": "act:it_act_2000",
                        "name": "Information Technology Act, 2000",
                        "title": "Information Technology Act, 2000",
                        "jurisdiction": "Union of India",
                    },
                    "label_type": "Act",
                },
            ]
            return MockAsyncResult(records)

        # Match single node lookup
        if "MATCH (n {id: $node_id})" in query:
            node_id = params.get("node_id")
            if node_id == "article:constitution_of_india:21":
                return MockAsyncResult([{
                    "n": {
                        "id": "article:constitution_of_india:21",
                        "name": "Article 21 - Protection of Life and Personal Liberty",
                        "title": "Article 21",
                        "jurisdiction": "Union of India",
                    },
                    "label_type": "Article",
                }])
            return MockAsyncResult([])

        # Match multi-hop traversal query
        if "MATCH p=(seed)-[rels" in query:
            path_records = [
                {
                    "path_nodes": [
                        {
                            "id": "article:constitution_of_india:21",
                            "name": "Article 21",
                            "labels": ["Article"],
                            "properties": {"name": "Article 21"},
                        },
                        {
                            "id": "judgment:maneka_gandhi",
                            "name": "Maneka Gandhi v. Union of India",
                            "labels": ["Judgment"],
                            "properties": {"name": "Maneka Gandhi v. Union of India"},
                        },
                    ],
                    "path_relationships": [
                        {
                            "type": "INTERPRETS",
                            "source_id": "judgment:maneka_gandhi",
                            "target_id": "article:constitution_of_india:21",
                            "provenance_key": "prov_maneka_art21",
                            "confidence": 0.98,
                            "document_id": "doc_maneka",
                            "chunk_id": "chunk_001",
                            "page": 5,
                            "evidence_text": "Expanded the scope of Article 21.",
                        }
                    ],
                }
            ]
            return MockAsyncResult(path_records)

        return MockAsyncResult([])


class MockDriver:
    def __init__(self, should_fail: bool = False):
        self._should_fail = should_fail

    def session(self, database: str | None = None):
        return MockAsyncSession(should_fail=self._should_fail)


class SeededNeo4jClient:
    def __init__(self, should_fail: bool = False):
        self.settings = type("SettingsMock", (), {
            "neo4j_database": "neo4j",
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_username": "neo4j",
            "neo4j_password": "password",
            "graph_max_hops": 3,
            "graph_max_nodes": 30,
        })()
        self._should_fail = should_fail

    async def _driver_for_use(self):
        if self._should_fail:
            raise RuntimeError("Driver could not establish connection to Neo4j Aura")
        return MockDriver(should_fail=self._should_fail)

    async def close(self):
        pass


@pytest.fixture
async def auth_admin(client, session):
    admin = User(email="graph_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()
    client.post("/auth/login", json={"email": "graph_admin@jurisai.law", "password": "password123"})
    yield client


@pytest.mark.asyncio
async def test_admin_graph_api_search_seeded_fixture(auth_admin):
    seeded_client = SeededNeo4jClient()
    app.dependency_overrides[get_graph_client] = lambda: seeded_client
    try:
        res = auth_admin.get("/graph/search?query=Article")
        assert res.status_code == 200
        data = res.json()
        assert "nodes" in data
        assert len(data["nodes"]) == 2
        assert data["total"] == 2

        node = data["nodes"][0]
        assert node["id"] == "article:constitution_of_india:21"
        assert "Article 21" in node["label"]
        assert node["type"] == "Article"
        assert "properties" in node
        assert node["properties"]["jurisdiction"] == "Union of India"
    finally:
        app.dependency_overrides.pop(get_graph_client, None)


@pytest.mark.asyncio
async def test_admin_graph_api_node_inspection(auth_admin):
    seeded_client = SeededNeo4jClient()
    app.dependency_overrides[get_graph_client] = lambda: seeded_client
    try:
        # Existing node
        res = auth_admin.get("/graph/nodes/article:constitution_of_india:21")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "article:constitution_of_india:21"
        assert data["type"] == "Article"

        # Missing node
        res_missing = auth_admin.get("/graph/nodes/non_existent_node_id")
        assert res_missing.status_code == 404
        assert "not found" in res_missing.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_graph_client, None)


@pytest.mark.asyncio
async def test_admin_graph_api_neighbors_and_bounding(auth_admin):
    seeded_client = SeededNeo4jClient()
    app.dependency_overrides[get_graph_client] = lambda: seeded_client
    try:
        # Valid neighbor traversal
        res = auth_admin.get("/graph/neighbors/article:constitution_of_india:21?depth=3")
        assert res.status_code == 200
        data = res.json()
        assert data["depth"] == 3
        assert data["center_node"] is not None
        assert data["center_node"]["id"] == "article:constitution_of_india:21"
        assert len(data["nodes"]) >= 1
        assert len(data["edges"]) >= 1

        edge = data["edges"][0]
        assert edge["sourceId"] == "judgment:maneka_gandhi"
        assert edge["targetId"] == "article:constitution_of_india:21"
        assert edge["label"] == "INTERPRETS"

        # Depth bounding at max 5
        res_max = auth_admin.get("/graph/neighbors/article:constitution_of_india:21?depth=5")
        assert res_max.status_code == 200
        assert res_max.json()["depth"] == 5

        # Invalid depth > 5 rejected with 422
        res_invalid = auth_admin.get("/graph/neighbors/article:constitution_of_india:21?depth=10")
        assert res_invalid.status_code == 422
    finally:
        app.dependency_overrides.pop(get_graph_client, None)


@pytest.mark.asyncio
async def test_admin_graph_api_subgraph(auth_admin):
    seeded_client = SeededNeo4jClient()
    app.dependency_overrides[get_graph_client] = lambda: seeded_client
    try:
        res = auth_admin.get("/graph/subgraph?node_ids=article:constitution_of_india:21&depth=2")
        assert res.status_code == 200
        data = res.json()
        assert len(data["nodes"]) >= 1
        assert len(data["edges"]) >= 1
    finally:
        app.dependency_overrides.pop(get_graph_client, None)


@pytest.mark.asyncio
async def test_admin_graph_database_unavailability_visible(auth_admin):
    failing_client = SeededNeo4jClient(should_fail=True)
    app.dependency_overrides[get_graph_client] = lambda: failing_client
    try:
        # Unavailability must return 503, never silently returning 200 with empty nodes
        res_search = auth_admin.get("/graph/search?query=Article")
        assert res_search.status_code == 503
        assert "unavailable" in res_search.json()["detail"].lower()

        res_node = auth_admin.get("/graph/nodes/article:constitution_of_india:21")
        assert res_node.status_code == 503
        assert "unavailable" in res_node.json()["detail"].lower()

        res_neighbors = auth_admin.get("/graph/neighbors/article:constitution_of_india:21")
        assert res_neighbors.status_code == 503
        assert "unavailable" in res_neighbors.json()["detail"].lower()

        res_subgraph = auth_admin.get("/graph/subgraph?node_ids=article:constitution_of_india:21")
        assert res_subgraph.status_code == 503
        assert "unavailable" in res_subgraph.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_graph_client, None)


@pytest.mark.asyncio
async def test_admin_graph_api_populate(auth_admin):
    seeded_client = SeededNeo4jClient()
    app.dependency_overrides[get_graph_client] = lambda: seeded_client
    try:
        res = auth_admin.post("/graph/populate?limit=5")
        assert res.status_code == 200
        data = res.json()
        assert "processed" in data
        assert "skipped" in data
        assert "successes" in data
        assert "failures" in data
    finally:
        app.dependency_overrides.pop(get_graph_client, None)

