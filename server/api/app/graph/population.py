"""Phase 4 graph population — READY PostgreSQL chunks to provenance-linked Neo4j."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.client import Neo4jClient
from app.graph.extraction import (
    Entity,
    Relation,
    contains_provenance_key,
    entity_properties,
    entity_provenance_key,
    extract_entities,
    extract_relations,
    source_fingerprint,
)
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus, ProcessingJobStage, ProcessingJobStatus
from app.models.processing_job import ProcessingJob

logger = logging.getLogger(__name__)

_EXTRACTION_METHOD = "deterministic_rule"


def _hierarchy_for_neo4j(hierarchy: dict[str, Any] | None) -> dict[str, Any]:
    """Drop JSON nulls; Neo4j map properties cannot contain null values."""
    return {key: value for key, value in (hierarchy or {}).items() if value is not None}


@dataclass
class DocumentPopulationOutcome:
    document_id: str
    title: str
    success: bool
    error: str | None = None
    entity_count: int = 0
    relation_count: int = 0


@dataclass
class PopulationSummary:
    processed: int = 0
    successes: list[DocumentPopulationOutcome] = field(default_factory=list)
    failures: list[DocumentPopulationOutcome] = field(default_factory=list)
    skipped: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "processed": self.processed,
            "skipped": self.skipped,
            "successes": [outcome.__dict__ for outcome in self.successes],
            "failures": [outcome.__dict__ for outcome in self.failures],
        }


async def _get_or_create_job(
    db: AsyncSession,
    document_id: UUID,
    stage: ProcessingJobStage,
) -> ProcessingJob:
    result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.stage == stage,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        job = ProcessingJob(
            document_id=document_id,
            stage=stage,
            status=ProcessingJobStatus.PENDING,
        )
        db.add(job)
        await db.flush()
    return job


async def _mark_job(
    db: AsyncSession,
    job: ProcessingJob,
    status: ProcessingJobStatus,
    error: str | None = None,
) -> None:
    job.status = status
    job.error = error
    await db.flush()


def _build_graph_payload(
    document: Document,
    chunks: list[Chunk],
    entities_by_chunk: dict[str, list[Entity]],
    relations_by_chunk: dict[str, list[Relation]],
) -> dict[str, Any]:
    document_id = str(document.id)
    chunk_rows: list[dict[str, Any]] = []
    entity_nodes: dict[str, dict[str, Any]] = {}
    supported_by: list[dict[str, Any]] = []
    defines: list[dict[str, Any]] = []
    other_relations: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_id = str(chunk.id)
        chunk_rows.append(
            {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_index": chunk.chunk_index,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "citation_ref": chunk.citation_ref,
                "hierarchy_json": _hierarchy_for_neo4j(chunk.hierarchy),
                "provenance_key": contains_provenance_key(document_id, chunk_id),
                "extraction_method": _EXTRACTION_METHOD,
            }
        )
        for entity in entities_by_chunk.get(chunk_id, []):
            props = entity_properties(entity)
            entity_nodes[entity.id] = {
                "label": entity.label,
                "id": props["id"],
                "name": props["name"],
                "confidence": props["confidence"],
            }
            supported_by.append(
                {
                    "source_id": entity.id,
                    "target_id": chunk_id,
                    "provenance_key": entity_provenance_key(chunk_id, entity.id),
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "confidence": entity.confidence,
                    "extraction_method": _EXTRACTION_METHOD,
                }
            )
        for relation in relations_by_chunk.get(chunk_id, []):
            rel_dict = {
                "type": relation.type,
                "source_id": relation.source_id,
                "target_id": relation.target_id,
                "provenance_key": source_fingerprint(chunk_id, relation),
                "document_id": document_id,
                "chunk_id": chunk_id,
                "page": relation.page or chunk.page_start,
                "evidence_text": relation.evidence_text,
                "confidence": relation.confidence,
                "extraction_method": relation.extraction_method,
            }
            if relation.type == "DEFINES":
                defines.append(rel_dict)
            else:
                other_relations.append(rel_dict)

    return {
        "document_id": document_id,
        "document": {
            "id": document_id,
            "title": document.title,
            "document_type": document.type.value,
        },
        "chunks": chunk_rows,
        "entity_nodes": list(entity_nodes.values()),
        "supported_by": supported_by,
        "defines": defines,
        "relations": other_relations,
    }



async def _populate_one_document(
    db: AsyncSession,
    client: Neo4jClient,
    document: Document,
) -> DocumentPopulationOutcome:
    document_id = document.id
    outcome = DocumentPopulationOutcome(
        document_id=str(document_id),
        title=document.title,
        success=False,
    )
    chunks = list(
        (
            await db.execute(
                select(Chunk)
                .where(Chunk.document_id == document_id)
                .order_by(Chunk.chunk_index)
            )
        ).scalars()
    )
    if not chunks:
        outcome.error = "No chunks found for READY document"
        return outcome

    job_entity = await _get_or_create_job(db, document_id, ProcessingJobStage.ENTITY_EXTRACTION)
    job_relation = await _get_or_create_job(db, document_id, ProcessingJobStage.RELATION_EXTRACTION)
    job_graph = await _get_or_create_job(db, document_id, ProcessingJobStage.GRAPH_POPULATION)

    entities_by_chunk: dict[str, list[Entity]] = {}
    relations_by_chunk: dict[str, list[Relation]] = {}
    total_entities = 0
    total_relations = 0

    try:
        await _mark_job(db, job_entity, ProcessingJobStatus.RUNNING)
        for chunk in chunks:
            chunk_id = str(chunk.id)
            entities = extract_entities(
                chunk.text,
                document_title=document.title,
                document_id=str(document_id),
            )
            entities_by_chunk[chunk_id] = entities
            total_entities += len(entities)
        await _mark_job(db, job_entity, ProcessingJobStatus.COMPLETED)
        await db.commit()
    except Exception as exc:
        await _mark_job(db, job_entity, ProcessingJobStatus.FAILED, str(exc))
        outcome.error = f"Entity extraction failed: {exc}"
        await db.commit()
        return outcome

    try:
        await _mark_job(db, job_relation, ProcessingJobStatus.RUNNING)
        for chunk in chunks:
            chunk_id = str(chunk.id)
            entities = entities_by_chunk[chunk_id]
            relations = extract_relations(
                chunk.text,
                entities,
                document_title=document.title,
                document_id=str(document_id),
            )
            relations_by_chunk[chunk_id] = relations
            total_relations += len(relations)
        await _mark_job(db, job_relation, ProcessingJobStatus.COMPLETED)
        await db.commit()
    except Exception as exc:
        await _mark_job(db, job_relation, ProcessingJobStatus.FAILED, str(exc))
        outcome.error = f"Relation extraction failed: {exc}"
        await db.commit()
        return outcome

    payload = _build_graph_payload(document, chunks, entities_by_chunk, relations_by_chunk)
    outcome.entity_count = total_entities
    outcome.relation_count = total_relations

    try:
        await _mark_job(db, job_graph, ProcessingJobStatus.RUNNING)
        await db.flush()
        await client.replace_document_graph(payload)
        await _mark_job(db, job_graph, ProcessingJobStatus.COMPLETED)
        await db.commit()
        outcome.success = True
        return outcome
    except Exception as exc:
        await _mark_job(db, job_graph, ProcessingJobStatus.FAILED, str(exc))
        await db.commit()
        outcome.error = f"Graph population failed: {exc}"
        logger.exception("Graph population failed for document %s", document_id)
        return outcome


async def populate_graph(
    db: AsyncSession,
    client: Neo4jClient,
    *,
    document_id: UUID | None = None,
    limit: int | None = None,
    clear: bool = False,
) -> PopulationSummary:
    """Populate Neo4j from READY documents; failures are isolated per document."""
    summary = PopulationSummary()
    if clear and document_id is None:
        await client.clear_graph()

    query = select(Document).where(Document.status == DocumentStatus.READY)
    if document_id is not None:
        query = query.where(Document.id == document_id)
    query = query.order_by(Document.created_at)
    if limit is not None:
        query = query.limit(limit)

    documents = (await db.execute(query)).scalars().all()
    if document_id is not None and not documents:
        summary.skipped = 1
        summary.failures.append(
            DocumentPopulationOutcome(
                document_id=str(document_id),
                title="",
                success=False,
                error="Document not found or not READY",
            )
        )
        return summary

    for document in documents:
        summary.processed += 1
        outcome = await _populate_one_document(db, client, document)
        if outcome.success:
            summary.successes.append(outcome)
        else:
            summary.failures.append(outcome)

    return summary


async def graph_stats(client: Neo4jClient) -> dict[str, Any]:
    """Return connectivity plus node/relationship counts and orphan entities."""
    try:
        health = await client.health()
    except Exception as exc:
        return {"connectivity": "unavailable", "error": str(exc)}
    stats = await client.statistics()
    return {"connectivity": "ok", "health": health, **stats}
