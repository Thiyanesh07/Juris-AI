"""Structured LLM output parsing and citation validation."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.qa.prompts import strip_optional_json_fence
from app.schemas.hybrid import HybridEvidence
from app.schemas.qa import QACitation

# Citation markers are [n] with 1–2 digits (evidence ranks). Years and other
# bracketed numbers such as [2024] are not treated as evidence markers.
# Legal phrasing like "Section [1]" is still a citation marker by design.
_MARKER_PATTERN = re.compile(r"\[(\d{1,2})\]")


class LLMOutputCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marker: int = Field(ge=1)
    evidence_rank: int = Field(ge=1)


class LLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    insufficient_evidence: bool
    citations: list[LLMOutputCitation] = Field(default_factory=list)


class CitationValidationError(ValueError):
    """Raised when model citations fail validation rules."""


class LLMOutputParseError(ValueError):
    """Raised when model output is not valid structured JSON."""


def parse_llm_output(raw: str) -> LLMOutput:
    """Parse and validate the model JSON object (optional single fence allowed)."""
    text = strip_optional_json_fence(raw)
    if text.lstrip().startswith("["):
        raise LLMOutputParseError("Expected a JSON object, not an array")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputParseError("Invalid JSON in model output") from exc
    if not isinstance(payload, dict):
        raise LLMOutputParseError("Expected a JSON object")
    try:
        return LLMOutput.model_validate(payload)
    except ValidationError as exc:
        raise LLMOutputParseError("Model JSON failed schema validation") from exc


def _markers_in_answer(answer: str) -> set[int]:
    return {int(match) for match in _MARKER_PATTERN.findall(answer) if int(match) >= 1}


def validate_llm_citations(
    output: LLMOutput,
    *,
    evidence_count: int,
) -> list[LLMOutputCitation]:
    """Validate citation rules; return deduplicated citations used in the answer."""
    if evidence_count < 0:
        raise CitationValidationError("Invalid evidence count")

    markers_in_answer = _markers_in_answer(output.answer)
    by_marker: dict[int, LLMOutputCitation] = {}

    for citation in output.citations:
        if citation.marker != citation.evidence_rank:
            raise CitationValidationError(
                "Citation marker must equal evidence_rank"
            )
        if not 1 <= citation.evidence_rank <= evidence_count:
            raise CitationValidationError("Citation evidence_rank out of range")
        by_marker[citation.marker] = citation

    for marker in markers_in_answer:
        if marker not in by_marker:
            raise CitationValidationError(
                f"Answer marker [{marker}] has no matching citation"
            )

    used = [by_marker[marker] for marker in sorted(markers_in_answer) if marker in by_marker]

    if not output.insufficient_evidence:
        if not output.answer.strip():
            raise CitationValidationError(
                "Answer text is required when insufficient_evidence is false"
            )
        if not used:
            raise CitationValidationError(
                "At least one citation is required when evidence is present"
            )

    return used


def build_public_citations(
    validated: list[LLMOutputCitation],
    evidence_items: list[HybridEvidence],
) -> list[QACitation]:
    """Map validated LLM citations onto server-side evidence metadata."""
    public: list[QACitation] = []
    for citation in validated:
        item = evidence_items[citation.evidence_rank - 1]
        public.append(
            QACitation(
                marker=citation.marker,
                evidence_rank=citation.evidence_rank,
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                document_title=item.document_title,
                document_version_id=item.document_version_id,
                chunk_index=item.chunk_index,
                citation_ref=item.citation_ref,
                page_start=item.page_start,
                page_end=item.page_end,
                source_url=item.source_url,
            )
        )
    return public


def validation_problem_message(exc: BaseException) -> str:
    if isinstance(exc, LLMOutputParseError):
        return str(exc)
    if isinstance(exc, CitationValidationError):
        return str(exc)
    return "Model output failed validation"


__all__ = [
    "CitationValidationError",
    "LLMOutput",
    "LLMOutputCitation",
    "LLMOutputParseError",
    "build_public_citations",
    "parse_llm_output",
    "validate_llm_citations",
    "validation_problem_message",
]
