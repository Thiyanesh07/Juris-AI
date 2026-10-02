"""Official Neo4j driver wrapper with parameterized, bounded graph operations."""
from __future__ import annotations

from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import Settings

_LABELS = {
    "Article",
    "Act",
    "Section",
    "Amendment",
    "Judgment",
    "Court",
    "Rule",
    "Regulation",
    "Concept",
    "Person",
    "Organization",
    "Document",
    "Chunk",
    "Doctrine",
    "Constitution",
}
_RELATION_TYPES = {
    "BELONGS_TO",
    "CONTAINS",
    "DEFINES",
    "REFERENCES",
    "INTERPRETS",
    "AMENDS",
    "MODIFIES",
    "CONFLICTS_WITH",
    "OVERRULES",
    "APPLIES_TO",
    "HELD",
    "DECIDED_BY",
    "CITED_BY",
    "RELATED_TO",
    "SUPPORTED_BY",
    "CITES",
    "CONSIDERS",
    "SUPERSEDES",
    "APPLIES",
}
_LEGAL_ENTITY_LABELS = (
    "Article",
    "Section",
    "Act",
    "Court",
    "Concept",
    "Amendment",
    "Judgment",
    "Rule",
    "Regulation",
    "Person",
    "Organization",
    "Doctrine",
    "Constitution",
)



class GraphError(RuntimeError):
    pass


class Neo4jClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._driver: Any | None = None

    async def _driver_for_use(self) -> Any:
        if self._driver is None:
            try:
                from neo4j import AsyncGraphDatabase
            except ImportError as exc:  # pragma: no cover
                raise GraphError("Neo4j driver is not installed; run `uv sync`.") from exc
            self._driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_username, self.settings.neo4j_password),
            )
        return self._driver

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def execute_write(
        self,
        work: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Run ``work`` inside a single Neo4j write transaction (commit or rollback)."""
        driver = await self._driver_for_use()
        async with driver.session(database=self.settings.neo4j_database) as session:
            return await session.execute_write(work)

    async def health(self) -> dict[str, Any]:
        try:
            driver = await self._driver_for_use()
            await driver.verify_connectivity()
            async with driver.session(database=self.settings.neo4j_database) as session:
                record = await (
                    await session.run(
                        "CALL dbms.components() YIELD name, versions "
                        "RETURN name, versions[0] AS version LIMIT 1"
                    )
                ).single()
            return {"status": "ok", "name": record["name"], "version": record["version"]}
        except Exception as exc:
            raise GraphError("Neo4j is unavailable") from exc

    async def ensure_schema(self) -> None:
        driver = await self._driver_for_use()
        async with driver.session(database=self.settings.neo4j_database) as session:
            for label in sorted(_LABELS):
                await session.run(
                    f"CREATE CONSTRAINT {label.lower()}_id_unique IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )

    async def clear_graph(self) -> None:
        """Remove every node and relationship in the configured database."""

        async def _clear(tx: Any) -> None:
            await tx.run("MATCH (n) DETACH DELETE n")

        await self.execute_write(_clear)

    async def merge_node(self, label: str, properties: dict[str, Any]) -> None:
        if label not in _LABELS or not properties.get("id"):
            raise GraphError("Invalid graph node label or stable ID")
        driver = await self._driver_for_use()
        async with driver.session(database=self.settings.neo4j_database) as session:
            await session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $properties",
                id=properties["id"],
                properties=properties,
            )

    async def merge_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict[str, Any],
    ) -> None:
        if relationship_type not in _RELATION_TYPES:
            raise GraphError("Invalid relationship type")
        if not properties.get("provenance_key"):
            raise GraphError("Relationship merge requires a provenance_key")
        driver = await self._driver_for_use()
        query = (
            f"MATCH (source {{id: $source_id}}), (target {{id: $target_id}}) "
            f"MERGE (source)-[r:{relationship_type} {{provenance_key: $provenance_key}}]->(target) "
            f"SET r += $properties"
        )
        async with driver.session(database=self.settings.neo4j_database) as session:
            await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                provenance_key=properties["provenance_key"],
                properties=properties,
            )

    async def replace_document_graph(self, payload: dict[str, Any]) -> None:
        """Atomically replace one document's subgraph (rollback on failure)."""

        async def _replace(tx: Any) -> None:
            document_id = payload["document_id"]
            await tx.run(
                """
                MATCH ()-[r:DEFINES]->()
                WHERE r.document_id = $document_id
                DELETE r
                """,
                document_id=document_id,
            )
            await tx.run(
                """
                MATCH (c:Chunk {document_id: $document_id})
                DETACH DELETE c
                """,
                document_id=document_id,
            )
            await tx.run(
                """
                MATCH (d:Document {id: $document_id})
                DETACH DELETE d
                """,
                document_id=document_id,
            )
            label_union = " OR ".join(f"n:{label}" for label in _LEGAL_ENTITY_LABELS)
            await tx.run(
                f"""
                MATCH (n)
                WHERE ({label_union})
                  AND NOT (n)-[:SUPPORTED_BY]->(:Chunk)
                DETACH DELETE n
                """,
            )

            document = payload["document"]
            await tx.run(
                """
                MERGE (d:Document {id: $id})
                SET d.title = $title,
                    d.document_type = $document_type
                """,
                id=document["id"],
                title=document["title"],
                document_type=document["document_type"],
            )

            for chunk in payload["chunks"]:
                await tx.run(
                    """
                    MERGE (c:Chunk {id: $id})
                    SET c.document_id = $document_id,
                        c.chunk_index = $chunk_index,
                        c.page_start = $page_start,
                        c.page_end = $page_end,
                        c.citation_ref = $citation_ref,
                        c.hierarchy_json = $hierarchy_json
                    WITH c
                    MATCH (d:Document {id: $document_id})
                    MERGE (d)-[r:CONTAINS {provenance_key: $provenance_key}]->(c)
                    SET r.document_id = $document_id,
                        r.chunk_id = $id,
                        r.confidence = 1.0,
                        r.extraction_method = $extraction_method
                    """,
                    **chunk,
                )

            for node in payload["entity_nodes"]:
                label = node["label"]
                if label not in _LABELS:
                    raise GraphError("Invalid graph node label or stable ID")
                await tx.run(
                    f"""
                    MERGE (n:{label} {{id: $id}})
                    SET n.name = $name, n.confidence = $confidence
                    """,
                    id=node["id"],
                    name=node["name"],
                    confidence=node["confidence"],
                )

            for rel in payload["supported_by"]:
                await tx.run(
                    """
                    MATCH (source {id: $source_id}), (target:Chunk {id: $target_id})
                    MERGE (source)-[r:SUPPORTED_BY {provenance_key: $provenance_key}]->(target)
                    SET r.document_id = $document_id,
                        r.chunk_id = $chunk_id,
                        r.confidence = $confidence,
                        r.extraction_method = $extraction_method
                    """,
                    **rel,
                )

            for rel in payload.get("defines", []):
                await tx.run(
                    """
                    MATCH (source {id: $source_id}), (target {id: $target_id})
                    MERGE (source)-[r:DEFINES {provenance_key: $provenance_key}]->(target)
                    SET r.document_id = $document_id,
                        r.chunk_id = $chunk_id,
                        r.confidence = $confidence,
                        r.extraction_method = $extraction_method
                    """,
                    **rel,
                )

            for rel in payload.get("relations", []):
                rel_type = rel.get("type")
                if rel_type and rel_type in _RELATION_TYPES:
                    await tx.run(
                        f"""
                        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
                        MERGE (source)-[r:{rel_type} {{provenance_key: $provenance_key}}]->(target)
                        SET r.document_id = $document_id,
                            r.chunk_id = $chunk_id,
                            r.page = $page,
                            r.evidence_text = $evidence_text,
                            r.confidence = $confidence,
                            r.extraction_method = $extraction_method
                        """,
                        source_id=rel["source_id"],
                        target_id=rel["target_id"],
                        provenance_key=rel["provenance_key"],
                        document_id=rel.get("document_id"),
                        chunk_id=rel.get("chunk_id"),
                        page=rel.get("page"),
                        evidence_text=rel.get("evidence_text", ""),
                        confidence=rel.get("confidence", 1.0),
                        extraction_method=rel.get("extraction_method", "deterministic_rule"),
                    )


        await self.execute_write(_replace)

    async def statistics(self) -> dict[str, Any]:
        driver = await self._driver_for_use()
        async with driver.session(database=self.settings.neo4j_database) as session:
            node_rows = [
                record
                async for record in await session.run(
                    "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS count"
                )
            ]
            rel_rows = [
                record
                async for record in await session.run(
                    "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count"
                )
            ]
            label_union = " OR ".join(f"n:{label}" for label in _LEGAL_ENTITY_LABELS)
            orphan = await (
                await session.run(
                    f"""
                    MATCH (n)
                    WHERE ({label_union})
                      AND NOT (n)-[:SUPPORTED_BY]->(:Chunk)
                    RETURN count(n) AS count
                    """
                )
            ).single()
        return {
            "nodes_by_label": dict(Counter({r["label"]: r["count"] for r in node_rows})),
            "relationships_by_type": dict(
                Counter({r["type"]: r["count"] for r in rel_rows})
            ),
            "orphan_legal_entities": orphan["count"],
        }

    async def traverse(
        self,
        seed_ids: list[str],
        max_hops: int,
        max_nodes: int,
    ) -> list[dict[str, Any]]:
        if not seed_ids:
            return []
        hops = min(max(max_hops, 1), self.settings.graph_max_hops)
        limit = min(max(max_nodes, 1), self.settings.graph_max_nodes)
        driver = await self._driver_for_use()
        query = (
            f"MATCH p=(seed)-[rels*1..{hops}]-(node) WHERE seed.id IN $seed_ids "
            "RETURN [n IN nodes(p) | properties(n)] AS nodes, "
            "[r IN relationships(p) | type(r)] AS relationships, "
            "[r IN relationships(p) | properties(r)] AS provenance LIMIT $limit"
        )
        async with driver.session(database=self.settings.neo4j_database) as session:
            rows = [
                record
                async for record in await session.run(query, seed_ids=seed_ids, limit=limit)
            ]
        return [
            {
                "nodes": row["nodes"],
                "relationships": row["relationships"],
                "provenance": row["provenance"],
            }
            for row in rows
        ]

    async def expand_supported_chunks(
        self,
        seed_ids: list[str],
        max_paths: int,
    ) -> list[dict[str, Any]]:
        """Two-hop SUPPORTED_BY expansion from seed chunks (read-only)."""
        if not seed_ids:
            return []
        if self.settings.graph_max_hops < 2:
            return []
        limit = min(max(max_paths, 1), 500)
        driver = await self._driver_for_use()
        query = """
            MATCH (seed:Chunk)<-[r1:SUPPORTED_BY]-(entity)-[r2:SUPPORTED_BY]->(candidate:Chunk)
            WHERE seed.id IN $seed_ids
              AND candidate.id <> seed.id
            WITH seed, entity, candidate, r1, r2
            ORDER BY seed.id, candidate.id, entity.id
            LIMIT $max_paths
            RETURN
              candidate.id AS chunk_id,
              seed.id AS seed_chunk_id,
              entity.id AS entity_id,
              labels(entity) AS entity_labels,
              entity.name AS entity_name,
              r1.confidence AS seed_edge_confidence,
              r2.confidence AS candidate_edge_confidence
            """
        async def _read_paths(tx: Any) -> list[Any]:
            result = await tx.run(
                query,
                seed_ids=seed_ids,
                max_paths=limit,
            )
            return [record async for record in result]

        async with driver.session(database=self.settings.neo4j_database) as session:
            rows = await session.execute_read(_read_paths)
        results: list[dict[str, Any]] = []
        for row in rows:
            chunk_id = row.get("chunk_id")
            seed_chunk_id = row.get("seed_chunk_id")
            entity_id = row.get("entity_id")
            if not chunk_id or not seed_chunk_id or not entity_id:
                continue
            labels = row.get("entity_labels") or []
            entity_label = next(
                (label for label in labels if label in _LABELS and label != "Chunk"),
                labels[0] if labels else "Concept",
            )
            results.append(
                {
                    "chunk_id": str(chunk_id),
                    "seed_chunk_id": str(seed_chunk_id),
                    "entity_id": str(entity_id),
                    "entity_label": str(entity_label),
                    "entity_name": str(row.get("entity_name") or ""),
                    "seed_edge_confidence": row.get("seed_edge_confidence"),
                    "candidate_edge_confidence": row.get("candidate_edge_confidence"),
                }
            )
        return results
