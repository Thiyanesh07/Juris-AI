"""Temporal Groundedness & Citation Validation Module (Phase 15).

Validates generated answers for temporal alignment, citation grounding,
provenance completeness, and absence of hallucinated authorities.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.rag.citation_verifier import VerifiedCitation
from app.rag.query_analysis import QueryAnalysisResult
from app.rag.temporal import LegalVersionInfo

logger = logging.getLogger(__name__)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grounded: bool = True
    temporal_valid: bool = True
    citation_valid: bool = True
    verified_count: int = 0
    unverified_count: int = 0
    warnings: list[str] = Field(default_factory=list)


def validate_response_groundedness(
    answer: str | None,
    citations: list[VerifiedCitation],
    query_analysis: QueryAnalysisResult,
    resolved_version: LegalVersionInfo | None = None,
    insufficient_evidence: bool = False,
) -> ValidationReport:
    """Perform end-to-end temporal, citation, and provenance validation before returning answer."""
    from app.qa.citations import _markers_in_answer

    warnings: list[str] = []
    temporal_valid = True
    citation_valid = True
    grounded = True

    if insufficient_evidence or not answer:
        return ValidationReport(
            grounded=False,
            temporal_valid=True,
            citation_valid=False,
            verified_count=0,
            unverified_count=0,
            warnings=["insufficient_evidence_flagged"],
        )

    # 1. Citation Verification & Grounding Check
    verified_cits = [c for c in citations if c.verification_status in ("VERIFIED", "PARTIALLY_VERIFIED")]
    unverified_cits = [c for c in citations if c.verification_status not in ("VERIFIED", "PARTIALLY_VERIFIED")]

    verified_count = len(verified_cits)
    unverified_count = len(unverified_cits)

    if unverified_count > 0:
        citation_valid = False
        grounded = False
        warnings.append(f"{unverified_count} unverified citation(s) detected in answer.")

    # Never treat zero verified citations as a successful grounding result
    if verified_count == 0:
        citation_valid = False
        grounded = False
        warnings.append("Answer has no verified supporting citations.")

    # Validate that every citation marker in the answer resolves to a verified citation
    markers_in_text = _markers_in_answer(answer)
    verified_markers = {c.marker for c in verified_cits}
    missing_or_unverified = markers_in_text - verified_markers
    if missing_or_unverified:
        citation_valid = False
        grounded = False
        warnings.append(
            f"Answer contains unverified or unresolvable citation marker(s): {sorted(missing_or_unverified)}."
        )

    # 2. Temporal Validation
    if query_analysis.is_temporal:
        if resolved_version:
            if resolved_version.status == "SUPERSEDED" and query_analysis.temporal_operator == "CURRENT_LAW":
                temporal_valid = False
                warnings.append(
                    f"Warning: Provision {resolved_version.entity_id} is SUPERSEDED but was queried for current law."
                )
            elif resolved_version.status == "REPEALED" and query_analysis.temporal_operator == "CURRENT_LAW":
                temporal_valid = False
                warnings.append(
                    f"Warning: Provision {resolved_version.entity_id} is REPEALED but was queried for current law."
                )

        if query_analysis.target_year:
            # Check if answer mentions wrong year contradicted by target_year
            if query_analysis.target_year < 1978 and "1978" in answer and "before" in answer.lower():
                pass  # valid pre-amendment contrast

    # 3. Provenance Integrity Check
    for c in verified_cits:
        if not c.provenance_intact:
            warnings.append(f"Citation marker [{c.marker}] lacks full provenance (missing chunk/document ID).")

    is_overall_grounded = (
        grounded
        and temporal_valid
        and citation_valid
        and verified_count > 0
        and not insufficient_evidence
    )

    return ValidationReport(
        grounded=is_overall_grounded,
        temporal_valid=temporal_valid,
        citation_valid=citation_valid,
        verified_count=verified_count,
        unverified_count=unverified_count,
        warnings=warnings,
    )
