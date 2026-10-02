"""Integration tests for the G01 application domain schema (real PostgreSQL).

These tests run against the throwaway test database created and migrated by
the ``conftest`` fixtures. The database layer is intentionally not mocked.
Requires the local Docker PostgreSQL service to be running (see conftest).
"""

import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Citation,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    EvaluationRun,
    ProcessingJob,
    ProcessingJobStage,
    ProcessingJobStatus,
    ResearchAnswer,
    ResearchQuery,
    ResearchSession,
    SavedResearch,
    SystemEvent,
    User,
    UserRole,
    ValidationStatus,
)

EXPECTED_TABLES = {
    "users",
    "research_sessions",
    "research_queries",
    "research_answers",
    "citations",
    "saved_research",
    "documents",
    "document_versions",
    "processing_jobs",
    "evaluation_runs",
    "system_events",
    "chunks",
    "alembic_version",
}


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        return await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))


async def test_database_connection_works(session: AsyncSession) -> None:
    result = await session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


async def test_migrated_schema_contains_all_tables(engine: AsyncEngine) -> None:
    names = await _table_names(engine)

    assert EXPECTED_TABLES.issubset(names)


async def test_user_can_be_created_with_defaults(session: AsyncSession) -> None:
    user = User(email="ada@example.com", name="Ada Lovelace")

    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.role is UserRole.USER
    assert isinstance(user.created_at, datetime) and user.created_at.tzinfo is not None
    assert isinstance(user.updated_at, datetime) and user.updated_at.tzinfo is not None


async def test_user_email_uniqueness_is_enforced(session: AsyncSession) -> None:
    session.add(User(email="dup@example.com"))
    await session.flush()

    session.add(User(email="dup@example.com"))

    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_user_session_query_answer_citation_chain(session: AsyncSession) -> None:
    user = User(email="chain@example.com", name="Chain User")
    research_session = ResearchSession(user=user, title="Article 21 research")
    query = ResearchQuery(session=research_session, question="What does Article 21 cover?")
    answer = ResearchAnswer(query=query, answer="Article 21 protects life and liberty.")
    citation = Citation(answer=answer, citation="[Art. 21, Constitution of India]", relevance=0.87)

    session.add_all([user, research_session, query, answer, citation])
    await session.commit()
    await session.refresh(citation)

    loaded = await session.scalar(
        select(User)
        .where(User.email == "chain@example.com")
        .options(
            selectinload(User.sessions)
            .selectinload(ResearchSession.queries)
            .selectinload(ResearchQuery.answers)
            .selectinload(ResearchAnswer.citations)
        )
    )

    assert loaded is not None
    assert loaded.sessions[0].title == "Article 21 research"
    first_query = loaded.sessions[0].queries[0]
    assert first_query.question == "What does Article 21 cover?"
    first_answer = first_query.answers[0]
    assert first_answer.validation_status is ValidationStatus.PENDING
    assert first_answer.citations[0].citation == "[Art. 21, Constitution of India]"
    assert first_answer.citations[0].answer_id == answer.id


async def test_saved_research_rejects_duplicate_user_session(session: AsyncSession) -> None:
    user = User(email="saver@example.com")
    research_session = ResearchSession(user=user, title="Saved thread")
    session.add_all([user, research_session])
    await session.flush()

    session.add(SavedResearch(user=user, session=research_session))
    await session.flush()
    session.add(SavedResearch(user=user, session=research_session))

    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_document_supports_versions_and_jobs(session: AsyncSession) -> None:
    document = Document(
        title="Constitution of India",
        type=DocumentType.CONSTITUTION,
        source="India Code",
        source_url="https://www.indiacode.nic.in",
    )
    current = DocumentVersion(
        document=document,
        version="as-of-2024",
        effective_from=date(2024, 1, 26),
        effective_to=None,
    )
    historical = DocumentVersion(
        document=document,
        version="as-of-1977",
        effective_from=date(1977, 1, 1),
        effective_to=date(2024, 1, 25),
    )
    job = ProcessingJob(
        document=document,
        stage=ProcessingJobStage.INGESTION,
        status=ProcessingJobStatus.PENDING,
    )

    session.add_all([document, current, historical, job])
    await session.commit()

    loaded = await session.scalar(
        select(Document)
        .where(Document.title == "Constitution of India")
        .options(selectinload(Document.versions), selectinload(Document.processing_jobs))
    )

    assert loaded is not None
    assert {version.version for version in loaded.versions} == {"as-of-2024", "as-of-1977"}
    assert any(version.effective_to is None for version in loaded.versions)
    assert all(isinstance(version.effective_from, date) for version in loaded.versions)
    assert loaded.processing_jobs[0].stage is ProcessingJobStage.INGESTION
    assert loaded.status is DocumentStatus.REGISTERED


async def test_document_version_rejects_inverted_date_range(session: AsyncSession) -> None:
    document = Document(title="Inverted Range Act", type=DocumentType.ACT, source="India Code")
    session.add(document)
    await session.flush()

    session.add(
        DocumentVersion(
            document=document,
            version="bad",
            effective_from=date(2020, 1, 1),
            effective_to=date(2019, 1, 1),
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_document_version_label_uniqueness(session: AsyncSession) -> None:
    document = Document(title="Versioned Act", type=DocumentType.ACT, source="India Code")
    session.add(document)
    await session.flush()

    session.add(DocumentVersion(document=document, version="v1", effective_from=date(2000, 1, 1)))
    await session.flush()
    session.add(DocumentVersion(document=document, version="v1", effective_from=date(2010, 1, 1)))

    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_document_registry_covers_allowed_types(session: AsyncSession) -> None:
    documents = [
        Document(title=title, type=doc_type, source="India Code")
        for title, doc_type in [
            ("Constitution of India", DocumentType.CONSTITUTION),
            ("Indian Penal Code", DocumentType.STATUTE),
            ("Supreme Court Ruling", DocumentType.JUDGMENT),
            ("Notification Rule", DocumentType.RULE),
        ]
    ]

    session.add_all(documents)
    await session.commit()

    count = await session.scalar(select(func.count()).select_from(Document))
    assert count == 4


async def test_invalid_enum_value_is_rejected(session: AsyncSession) -> None:
    with pytest.raises((StatementError, LookupError)):
        session.add(
            Document(
                title="Bad Status",
                type=DocumentType.ACT,
                source="India Code",
                status="bogus-status",
            )
        )
        await session.flush()


async def test_evaluation_run_jsonb_roundtrip(session: AsyncSession) -> None:
    configuration = {"retriever": "hybrid", "k": 10, "hops": 2}

    session.add(
        EvaluationRun(
            name="baseline-dense-only",
            configuration=configuration,
            results={"recall_at_5": 0.42},
        )
    )
    await session.commit()

    loaded = await session.scalar(
        select(EvaluationRun).where(EvaluationRun.name == "baseline-dense-only")
    )

    assert loaded is not None
    assert loaded.configuration == configuration
    assert loaded.results == {"recall_at_5": 0.42}


async def test_system_event_keeps_actor_and_metadata(session: AsyncSession) -> None:
    user = User(email="actor@example.com")
    event = SystemEvent(
        event_type="document.registered",
        actor=user,
        event_metadata={"document_title": "An Act"},
    )

    session.add_all([user, event])
    await session.commit()
    await session.refresh(event)

    assert event.actor_id == user.id
    assert event.event_metadata == {"document_title": "An Act"}
    assert event.created_at.tzinfo is not None


async def test_deleting_user_cascades_research_data(session: AsyncSession) -> None:
    user = User(email="cascade@example.com")
    research_session = ResearchSession(user=user, title="Doomed session")
    query = ResearchQuery(session=research_session, question="Doomed question?")
    answer = ResearchAnswer(query=query, answer="Doomed answer.")
    citation = Citation(answer=answer, citation="[Doomed citation]")
    saved = SavedResearch(user=user, session=research_session)

    session.add_all([user, research_session, query, answer, citation, saved])
    await session.commit()

    await session.delete(user)
    await session.commit()

    for model in (ResearchSession, ResearchQuery, ResearchAnswer, Citation, SavedResearch):
        count = await session.scalar(select(func.count()).select_from(model))
        assert count == 0


async def test_deleting_document_cascades_versions_and_jobs(session: AsyncSession) -> None:
    document = Document(title="Doomed Doc", type=DocumentType.ACT, source="India Code")
    version = DocumentVersion(document=document, version="v1", effective_from=date(2001, 1, 1))
    job = ProcessingJob(document=document, stage=ProcessingJobStage.CHUNKING)

    session.add_all([document, version, job])
    await session.commit()

    await session.delete(document)
    await session.commit()

    assert await session.scalar(select(func.count()).select_from(DocumentVersion)) == 0
    assert await session.scalar(select(func.count()).select_from(ProcessingJob)) == 0


async def test_document_with_citations_is_protected_from_deletion(
    session: AsyncSession,
) -> None:
    user = User(email="citer@example.com")
    research_session = ResearchSession(user=user, title="Citing session")
    query = ResearchQuery(session=research_session, question="Q?")
    answer = ResearchAnswer(query=query, answer="A")
    document = Document(title="Cited Act", type=DocumentType.ACT, source="India Code")
    citation = Citation(answer=answer, document=document, citation="[Cited Act]")

    session.add_all([user, research_session, query, answer, document, citation])
    await session.commit()

    await session.delete(document)

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()
    assert await session.scalar(select(func.count()).select_from(Document)) == 1
