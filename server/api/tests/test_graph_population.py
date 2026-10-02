"""Graph population orchestration tests (PostgreSQL + in-memory Neo4j)."""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.population import graph_stats, populate_graph
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType, ProcessingJobStage, ProcessingJobStatus
from app.models.processing_job import ProcessingJob
from tests.fake_neo4j import FakeNeo4jClient


async def _ready_document(
    session: AsyncSession,
    *,
    title: str = "Indian Penal Code",
    status: DocumentStatus = DocumentStatus.READY,
    text: str = "Section 1 intro. Section 2 defines person for this Act.",
) -> Document:
    doc = Document(title=title, type=DocumentType.ACT, source="test", status=status)
    session.add(doc)
    await session.flush()
    session.add(
        Chunk(
            document_id=doc.id,
            chunk_index=0,
            text=text,
            char_count=len(text),
            page_start=1,
            page_end=1,
            hierarchy={"section": "2"},
            citation_ref="Section 2",
        )
    )
    await session.commit()
    await session.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_ready_document_populates_graph(session: AsyncSession) -> None:
    doc = await _ready_document(session)
    client = FakeNeo4jClient()
    summary = await populate_graph(session, client)
    assert summary.ok
    assert summary.processed == 1
    assert client.graph.nodes[str(doc.id)]["title"] == doc.title


@pytest.mark.asyncio
async def test_document_and_chunk_nodes_without_text(session: AsyncSession) -> None:
    doc = await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client)
    chunk_id = (
        await session.execute(select(Chunk.id).where(Chunk.document_id == doc.id))
    ).scalar_one()
    chunk_node = client.graph.nodes[str(chunk_id)]
    assert "text" not in chunk_node
    assert client.graph.node_labels[str(chunk_id)] == "Chunk"


@pytest.mark.asyncio
async def test_contains_supported_by_and_defines(session: AsyncSession) -> None:
    await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client)
    rel_types = {rel.type for rel in client.graph.relationships}
    assert {"CONTAINS", "SUPPORTED_BY", "DEFINES"}.issubset(rel_types)


@pytest.mark.asyncio
async def test_idempotent_repopulation(session: AsyncSession) -> None:
    await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client)
    first_rel_count = len(client.graph.relationships)
    await populate_graph(session, client)
    assert len(client.graph.relationships) == first_rel_count


@pytest.mark.asyncio
async def test_rechunk_replaces_old_chunk_nodes(session: AsyncSession) -> None:
    doc = await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client)
    old_chunk_id = (
        await session.execute(select(Chunk.id).where(Chunk.document_id == doc.id))
    ).scalar_one()
    await session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    new_chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        text="Section 9 defines witness.",
        char_count=24,
        page_start=2,
        page_end=2,
        hierarchy={},
        citation_ref="Section 9",
    )
    session.add(new_chunk)
    await session.commit()
    await populate_graph(session, client, document_id=doc.id)
    assert str(old_chunk_id) not in client.graph.nodes
    assert str(new_chunk.id) in client.graph.nodes


@pytest.mark.asyncio
async def test_non_ready_document_skipped(session: AsyncSession) -> None:
    doc = await _ready_document(session, status=DocumentStatus.REGISTERED)
    client = FakeNeo4jClient()
    summary = await populate_graph(session, client, document_id=doc.id)
    assert summary.failures
    assert summary.failures[0].error == "Document not found or not READY"


@pytest.mark.asyncio
async def test_neo4j_failure_leaves_document_ready_and_marks_graph_job_failed(
    session: AsyncSession,
) -> None:
    doc = await _ready_document(session)
    client = FakeNeo4jClient()
    client.fail_next_replace = True
    summary = await populate_graph(session, client, document_id=doc.id)
    assert summary.failures
    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY
    jobs = (
        await session.execute(select(ProcessingJob).where(ProcessingJob.document_id == doc.id))
    ).scalars().all()
    by_stage = {job.stage: job for job in jobs}
    assert by_stage[ProcessingJobStage.ENTITY_EXTRACTION].status == ProcessingJobStatus.COMPLETED
    assert by_stage[ProcessingJobStage.RELATION_EXTRACTION].status == ProcessingJobStatus.COMPLETED
    assert by_stage[ProcessingJobStage.GRAPH_POPULATION].status == ProcessingJobStatus.FAILED


@pytest.mark.asyncio
async def test_subsequent_documents_run_after_failure(session: AsyncSession) -> None:
    first = await _ready_document(session, title="First Act")
    second = await _ready_document(session, title="Second Act")
    client = FakeNeo4jClient()

    original = client.replace_document_graph

    async def flaky_replace(payload: dict) -> None:
        if payload["document_id"] == str(first.id):
            raise RuntimeError("boom")
        await original(payload)

    client.replace_document_graph = flaky_replace  # type: ignore[method-assign]
    summary = await populate_graph(session, client, limit=10)
    assert len(summary.failures) == 1
    assert len(summary.successes) == 1
    assert not summary.ok
    assert str(second.id) in client.graph.nodes


@pytest.mark.asyncio
async def test_clear_wipes_graph_before_population(session: AsyncSession) -> None:
    await _ready_document(session)
    client = FakeNeo4jClient()
    client.graph.merge_node("Document", {"id": "stale", "title": "Stale", "document_type": "act"})
    await populate_graph(session, client, clear=True)
    assert "stale" not in client.graph.nodes


@pytest.mark.asyncio
async def test_clear_with_document_id_does_not_wipe_entire_graph(
    session: AsyncSession,
) -> None:
    first = await _ready_document(session, title="First Act")
    second = await _ready_document(session, title="Second Act")
    client = FakeNeo4jClient()
    await populate_graph(session, client)
    client.graph.merge_node("Document", {"id": "stale", "title": "Stale", "document_type": "act"})
    await populate_graph(session, client, document_id=first.id, clear=True)
    assert "stale" in client.graph.nodes
    assert str(second.id) in client.graph.nodes
    assert str(first.id) in client.graph.nodes


@pytest.mark.asyncio
async def test_limit_processes_whole_documents_only(session: AsyncSession) -> None:
    await _ready_document(session, title="First Act")
    await _ready_document(session, title="Second Act")
    await _ready_document(session, title="Third Act")
    client = FakeNeo4jClient()
    summary = await populate_graph(session, client, limit=2)
    assert summary.processed == 2
    assert len(summary.successes) == 2
    assert len(client.graph.nodes) > 0


@pytest.mark.asyncio
async def test_successful_jobs_complete_all_graph_stages(session: AsyncSession) -> None:
    doc = await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client, document_id=doc.id)
    jobs = (
        await session.execute(select(ProcessingJob).where(ProcessingJob.document_id == doc.id))
    ).scalars().all()
    by_stage = {job.stage: job for job in jobs}
    assert by_stage[ProcessingJobStage.ENTITY_EXTRACTION].status == ProcessingJobStatus.COMPLETED
    assert by_stage[ProcessingJobStage.RELATION_EXTRACTION].status == ProcessingJobStatus.COMPLETED
    assert by_stage[ProcessingJobStage.GRAPH_POPULATION].status == ProcessingJobStatus.COMPLETED
    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY


@pytest.mark.asyncio
async def test_extraction_failure_leaves_later_jobs_pending(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = await _ready_document(session)

    def boom(*_args: object, **_kwargs: object) -> list[object]:
        raise RuntimeError("extractor crashed")

    monkeypatch.setattr("app.graph.population.extract_entities", boom)
    client = FakeNeo4jClient()
    summary = await populate_graph(session, client, document_id=doc.id)
    assert summary.failures
    jobs = (
        await session.execute(select(ProcessingJob).where(ProcessingJob.document_id == doc.id))
    ).scalars().all()
    by_stage = {job.stage: job for job in jobs}
    assert by_stage[ProcessingJobStage.ENTITY_EXTRACTION].status == ProcessingJobStatus.FAILED
    assert by_stage[ProcessingJobStage.RELATION_EXTRACTION].status == ProcessingJobStatus.PENDING
    assert by_stage[ProcessingJobStage.GRAPH_POPULATION].status == ProcessingJobStatus.PENDING
    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY


@pytest.mark.asyncio
async def test_abc_partial_failure_continues(session: AsyncSession) -> None:
    first = await _ready_document(session, title="Alpha Act")
    second = await _ready_document(session, title="Beta Act")
    third = await _ready_document(session, title="Gamma Act")
    client = FakeNeo4jClient()
    original = client.replace_document_graph

    async def flaky_replace(payload: dict) -> None:
        if payload["document_id"] == str(second.id):
            raise RuntimeError("boom")
        await original(payload)

    client.replace_document_graph = flaky_replace  # type: ignore[method-assign]
    summary = await populate_graph(session, client)
    assert {outcome.document_id for outcome in summary.successes} == {
        str(first.id),
        str(third.id),
    }
    assert [outcome.document_id for outcome in summary.failures] == [str(second.id)]
    assert not summary.ok
    assert str(first.id) in client.graph.nodes
    assert str(second.id) not in client.graph.nodes
    assert str(third.id) in client.graph.nodes


@pytest.mark.asyncio
async def test_mid_replace_failure_does_not_leave_partial_graph(
    session: AsyncSession,
) -> None:
    doc = await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client, document_id=doc.id)
    before = dict(client.graph.nodes)
    client.fail_after_delete = True
    summary = await populate_graph(session, client, document_id=doc.id)
    assert summary.failures
    assert client.graph.nodes == before
    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY


@pytest.mark.asyncio
async def test_relationship_provenance_fields_are_present(session: AsyncSession) -> None:
    await _ready_document(session)
    client = FakeNeo4jClient()
    await populate_graph(session, client)
    required = {"provenance_key", "document_id", "chunk_id", "confidence", "extraction_method"}
    types_seen = {rel.type for rel in client.graph.relationships}
    assert {"CONTAINS", "SUPPORTED_BY", "DEFINES"} <= types_seen
    for rel in client.graph.relationships:
        assert required <= set(rel.properties)


@pytest.mark.asyncio
async def test_hierarchy_nulls_are_stripped_before_neo4j(session: AsyncSession) -> None:
    doc = await _ready_document(session)
    chunk = (
        await session.execute(select(Chunk).where(Chunk.document_id == doc.id))
    ).scalar_one()
    chunk.hierarchy = {"section": "2", "part": None, "proviso": False}
    await session.commit()
    client = FakeNeo4jClient()
    await populate_graph(session, client, document_id=doc.id)
    stored = client.graph.nodes[str(chunk.id)]["hierarchy_json"]
    assert "part" not in stored
    assert stored["section"] == "2"
    assert stored["proviso"] is False
    assert "text" not in client.graph.nodes[str(chunk.id)]


@pytest.mark.asyncio
async def test_graph_stats_reads_client_counts() -> None:
    client = FakeNeo4jClient()
    client.graph.merge_node("Document", {"id": "d1", "title": "T", "document_type": "act"})
    stats = await graph_stats(client)
    assert stats["connectivity"] == "ok"
    assert stats["nodes_by_label"]["Document"] == 1
    assert stats["orphan_legal_entities"] == 0


@pytest.mark.asyncio
async def test_non_ready_corpus_scan_does_not_touch_jobs(session: AsyncSession) -> None:
    doc = await _ready_document(session, status=DocumentStatus.REGISTERED)
    client = FakeNeo4jClient()
    summary = await populate_graph(session, client)
    assert summary.processed == 0
    await session.refresh(doc)
    assert doc.status == DocumentStatus.REGISTERED
    jobs = (
        await session.execute(select(ProcessingJob).where(ProcessingJob.document_id == doc.id))
    ).scalars().all()
    assert jobs == []
