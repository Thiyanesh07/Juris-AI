"""Startup recovery for interrupted processing jobs.

In a single-process deployment model (such as Render web services), any job left
in RUNNING status when the application process starts was interrupted by a server
restart, crash, or deployment.

This module safely recovers orphaned RUNNING jobs by marking them FAILED with
a descriptive error message, marking any associated PROCESSING documents as FAILED,
and allowing administrators to safely retry them without automatically triggering
re-execution at startup.
"""

from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import DocumentStatus, ProcessingJobStatus
from app.models.processing_job import ProcessingJob

logger = logging.getLogger(__name__)

INTERRUPTED_JOB_ERROR = (
    "Processing interrupted by server process restart. Administrator may safely retry."
)


async def recover_interrupted_jobs(session: AsyncSession) -> int:
    """Identify and mark orphaned RUNNING processing jobs as FAILED.

    Args:
        session: Active async database session.

    Returns:
        The number of recovered processing jobs.
    """
    result = await session.execute(
        select(ProcessingJob).where(ProcessingJob.status == ProcessingJobStatus.RUNNING)
    )
    running_jobs = list(result.scalars().all())

    if not running_jobs:
        return 0

    doc_ids_to_fail = set()
    for job in running_jobs:
        job.status = ProcessingJobStatus.FAILED
        job.error = INTERRUPTED_JOB_ERROR
        doc_ids_to_fail.add(job.document_id)

    if doc_ids_to_fail:
        doc_result = await session.execute(
            select(Document).where(
                Document.id.in_(doc_ids_to_fail),
                Document.status == DocumentStatus.PROCESSING,
            )
        )
        for doc in doc_result.scalars().all():
            doc.status = DocumentStatus.FAILED

    await session.commit()
    logger.warning(
        "Startup recovery: marked %d orphaned RUNNING job(s) across %d document(s) as FAILED.",
        len(running_jobs),
        len(doc_ids_to_fail),
    )
    return len(running_jobs)
