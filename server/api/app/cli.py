"""Developer entry points which reuse the API service layer."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import session_factory
from app.graph.client import Neo4jClient
from app.graph.population import graph_stats, populate_graph
from app.retrieval.embeddings import EmbeddingError
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.index import IndexError
from app.retrieval.service import rebuild_index, retrieve


async def _qa_query(query: str, top_k: int | None) -> int:
    from app.qa.provider import LLMProviderError
    from app.qa.service import QAInvalidModelOutputError, ask_legal_question

    settings = get_settings()
    client = Neo4jClient(settings)
    try:
        async with session_factory() as session:
            response = await ask_legal_question(
                session,
                client,
                query,
                top_k,
                settings,
            )
        print(response.model_dump_json(indent=2))
        return 0
    except (
        EmbeddingError,
        IndexError,
        SQLAlchemyError,
        ValueError,
        LLMProviderError,
        QAInvalidModelOutputError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        await client.close()


async def _rebuild() -> None:
    async with session_factory() as session:
        print(json.dumps(await rebuild_index(session, get_settings()), indent=2))


async def _populate_graph(
    document_id: UUID | None,
    limit: int | None,
    clear: bool,
) -> int:
    settings = get_settings()
    client = Neo4jClient(settings)
    try:
        await client.ensure_schema()
        async with session_factory() as session:
            summary = await populate_graph(
                session,
                client,
                document_id=document_id,
                limit=limit,
                clear=clear,
            )
        print(json.dumps(summary.to_dict(), indent=2))
        return 0 if summary.ok else 1
    finally:
        await client.close()


async def _hybrid_query(query: str, top_k: int | None) -> int:
    settings = get_settings()
    client = Neo4jClient(settings)
    try:
        async with session_factory() as session:
            payload = await hybrid_retrieve(
                session,
                client,
                query,
                top_k or settings.retrieval_default_top_k,
                settings,
            )
        print(json.dumps(payload, indent=2))
        return 0
    except (EmbeddingError, IndexError, SQLAlchemyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        await client.close()


async def _graph_stats() -> None:
    settings = get_settings()
    client = Neo4jClient(settings)
    try:
        print(json.dumps(await graph_stats(client), indent=2))
    finally:
        await client.close()


async def _create_super_admin(email: str, name: str | None) -> int:
    from sqlalchemy import select
    from app.models import User, UserRole

    async with session_factory() as session:
        normalized_email = email.lower().strip()
        user = await session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            user = User(
                email=normalized_email,
                name=name or "Super Admin",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
            )
            session.add(user)
        else:
            user.role = UserRole.SUPER_ADMIN
            user.is_active = True
            if name:
                user.name = name

        await session.commit()
        await session.refresh(user)

        res = {
            "status": "success",
            "message": "User provisioned as SUPER_ADMIN",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "is_active": user.is_active,
            },
        }
        print(json.dumps(res, indent=2))
        return 0


async def _ingest_corpus(document_id: str | None) -> int:
    from dataclasses import asdict
    from app.ingestion.corpus_pipeline import run_corpus_ingestion

    settings = get_settings()
    client = Neo4jClient(settings)
    try:
        try:
            await client.ensure_schema()
        except Exception as exc:
            print(f"Neo4j connectivity warning: {exc}", file=sys.stderr)
        report = run_corpus_ingestion(
            settings=settings,
            graph_client=client,
            single_doc_id=document_id,
        )
        print(json.dumps(asdict(report), indent=2))
        return 0 if report.documents_failed == 0 else 1
    finally:
        await client.close()


async def _import_corpus() -> int:
    from import_corpus import import_corpus
    try:
        stats = await import_corpus()
        print(json.dumps(stats, indent=2))
        return 0
    except Exception as exc:
        print(f"Import corpus failed: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(description="LegalGraph developer commands")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rebuild-index")
    ingest = commands.add_parser("ingest-corpus", help="Run Phase 13 Legal Knowledge Layer corpus ingestion")
    ingest.add_argument("--document-id", default=None, help="Process single document_id only")
    commands.add_parser("import-corpus", help="Import processed corpus metadata and chunks into PostgreSQL")
    query = commands.add_parser("query")
    query.add_argument("query")
    query.add_argument("--top-k", type=int, default=None)
    populate = commands.add_parser("populate-graph")
    populate.add_argument("--document-id", type=UUID, default=None)
    populate.add_argument("--clear", action="store_true")
    populate.add_argument("--limit", type=int, default=None)
    commands.add_parser("graph-stats")
    hybrid = commands.add_parser("hybrid-query")
    hybrid.add_argument("query")
    hybrid.add_argument("--top-k", type=int, default=None)
    qa = commands.add_parser("qa")
    qa.add_argument("query")
    qa.add_argument("--top-k", type=int, default=None)

    csa = commands.add_parser("create-super-admin", help="Provision a SUPER_ADMIN user")
    csa.add_argument("--email", required=True, help="Email address of the administrator")
    csa.add_argument("--name", default=None, help="Name of the administrator")

    args = parser.parse_args()
    if args.command == "rebuild-index":
        asyncio.run(_rebuild())
    elif args.command == "ingest-corpus":
        sys.exit(asyncio.run(_ingest_corpus(args.document_id)))
    elif args.command == "import-corpus":
        sys.exit(asyncio.run(_import_corpus()))
    elif args.command == "populate-graph":
        code = asyncio.run(_populate_graph(args.document_id, args.limit, args.clear))
        sys.exit(code)
    elif args.command == "graph-stats":
        asyncio.run(_graph_stats())
    elif args.command == "hybrid-query":
        sys.exit(asyncio.run(_hybrid_query(args.query, args.top_k)))
    elif args.command == "qa":
        sys.exit(asyncio.run(_qa_query(args.query, args.top_k)))
    elif args.command == "create-super-admin":
        sys.exit(asyncio.run(_create_super_admin(args.email, args.name)))
    else:
        settings = get_settings()
        print(
            json.dumps(
                retrieve(args.query, args.top_k or settings.retrieval_default_top_k, settings),
                indent=2,
            )
        )



if __name__ == "__main__":
    main()

