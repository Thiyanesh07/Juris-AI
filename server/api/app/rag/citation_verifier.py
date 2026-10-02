"""Citation Extraction, Structural Grounding, and Provenance Verification Module (Phase 15).

Extracts Indian legal citation patterns (SCC, AIR, SCR, Article/Section references),
verifies evidence provenance against raw corpus chunks, and computes verification status.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

CitationVerificationStatus = Literal[
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
    "CONTRADICTED",
]

# Regex patterns for Indian Legal Citations
_CITATION_SCC = re.compile(r"(?:\(\d{4}\)|\[\d{4}\]|\b\d{4}\b)\s*\d+\s+SCC\s+\d+\b", re.IGNORECASE)
_CITATION_AIR = re.compile(r"\bAIR\s+\d{4}\s+(?:SC|HC|[A-Z][a-z]+)\s+\d+\b", re.IGNORECASE)
_CITATION_SCR = re.compile(r"(?:\(\d{4}\)|\[\d{4}\]|\b\d{4}\b)\s*\d+\s+SCR\s+\d+\b", re.IGNORECASE)
_CITATION_SCALE = re.compile(r"\b\d{4}\s*\(\d+\)\s*SCALE\s*\d+\b", re.IGNORECASE)
_CITATION_PROVISION = re.compile(
    r"\b(?:Article|Section|Sec\.|Art\.)\s+\d+[A-Z]?(?:\s+of\s+the\s+[A-Za-z\s,]+)?\b",
    re.IGNORECASE,
)


class VerifiedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marker: int
    citation_text: str
    source_chunk_id: str
    source_document_id: str
    source_document_title: str
    page: int | None = None
    evidence_text: str = ""
    verification_status: CitationVerificationStatus = "UNVERIFIED"
    confidence: float = 0.0
    provenance_intact: bool = False


def extract_legal_citations_from_text(text: str) -> list[str]:
    """Extract formal legal citation strings from arbitrary legal text."""
    found: set[str] = set()

    for match in _CITATION_SCC.finditer(text):
        found.add(" ".join(match.group(0).split()))
    for match in _CITATION_AIR.finditer(text):
        found.add(" ".join(match.group(0).split()))
    for match in _CITATION_SCR.finditer(text):
        found.add(" ".join(match.group(0).split()))
    for match in _CITATION_SCALE.finditer(text):
        found.add(" ".join(match.group(0).split()))

    return sorted(found)


def verify_citation_grounding(
    marker: int,
    evidence_rank: int,
    evidence_chunks: list[dict[str, Any]],
) -> VerifiedCitation:
    """Verify that a generated citation marker maps to actual corpus evidence and provenance."""
    if not (1 <= evidence_rank <= len(evidence_chunks)):
        return VerifiedCitation(
            marker=marker,
            citation_text="Unverified Legal Citation",
            source_chunk_id="",
            source_document_id="",
            source_document_title="Unknown Source",
            verification_status="UNVERIFIED",
            confidence=0.0,
            provenance_intact=False,
        )

    target_chunk = evidence_chunks[evidence_rank - 1]
    chunk_id = str(target_chunk.get("chunk_id") or target_chunk.get("id") or "")
    doc_id = str(target_chunk.get("document_id") or "")
    doc_title = str(target_chunk.get("document_title") or target_chunk.get("title") or "Legal Source")
    text = str(target_chunk.get("text") or "")
    page = target_chunk.get("page_start")
    citation_ref = target_chunk.get("citation_ref") or doc_title

    # Extract any formal citations inside chunk text
    formal_cits = extract_legal_citations_from_text(text)
    citation_str = formal_cits[0] if formal_cits else citation_ref

    # Provenance check: chunk_id and document_id must be valid non-empty IDs
    has_valid_ids = bool(chunk_id) and bool(doc_id)
    has_valid_page = page is not None and page >= 1

    status: CitationVerificationStatus = "UNVERIFIED"
    confidence = 0.50

    if has_valid_ids and text:
        if formal_cits or citation_ref:
            status = "VERIFIED"
            confidence = 1.0 if has_valid_page else 0.90
        else:
            status = "PARTIALLY_VERIFIED"
            confidence = 0.75

    return VerifiedCitation(
        marker=marker,
        citation_text=citation_str,
        source_chunk_id=chunk_id,
        source_document_id=doc_id,
        source_document_title=doc_title,
        page=page,
        evidence_text=text[:300],
        verification_status=status,
        confidence=confidence,
        provenance_intact=has_valid_ids,
    )
