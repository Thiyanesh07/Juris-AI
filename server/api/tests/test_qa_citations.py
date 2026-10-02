"""Unit tests for LLM output parsing and citation validation."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from app.qa.citations import (
    CitationValidationError,
    LLMOutputParseError,
    build_public_citations,
    parse_llm_output,
    validate_llm_citations,
)
from app.schemas.hybrid import HybridEvidence


def _evidence(rank: int = 1) -> HybridEvidence:
    return HybridEvidence.model_validate(
        {
            "rank": rank,
            "chunk_id": UUID("00000000-0000-0000-0000-000000000001"),
            "document_id": UUID("00000000-0000-0000-0000-000000000010"),
            "document_title": "Constitution",
            "document_version_id": None,
            "chunk_index": 0,
            "text": "equality",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {},
            "citation_ref": "Article 14",
            "source_url": None,
            "dense_score": 1.0,
            "graph_score": 0.0,
            "hybrid_score": 0.7,
            "dense_rank": 1,
            "graph_rank": None,
            "dense_matched": True,
            "evidence_sources": ["dense"],
            "graph_context": None,
        }
    )


def _payload(**overrides: object) -> str:
    base = {
        "answer": "Equality applies [1].",
        "insufficient_evidence": False,
        "citations": [{"marker": 1, "evidence_rank": 1}],
    }
    base.update(overrides)
    return json.dumps(base)


def test_parse_valid_json() -> None:
    output = parse_llm_output(_payload())
    assert output.answer.startswith("Equality")


def test_parse_fenced_json() -> None:
    raw = "```json\n" + _payload() + "\n```"
    output = parse_llm_output(raw)
    assert output.citations[0].marker == 1


def test_parse_rejects_array() -> None:
    with pytest.raises(LLMOutputParseError):
        parse_llm_output("[]")


def test_parse_rejects_prose_before_json() -> None:
    with pytest.raises(LLMOutputParseError):
        parse_llm_output("Here is the answer:\n" + _payload())


def test_parse_rejects_prose_after_json() -> None:
    with pytest.raises(LLMOutputParseError):
        parse_llm_output(_payload() + "\nThanks")


def test_parse_rejects_multiple_objects() -> None:
    with pytest.raises(LLMOutputParseError):
        parse_llm_output(_payload() + _payload())


def test_parse_rejects_malformed_json() -> None:
    with pytest.raises(LLMOutputParseError):
        parse_llm_output("{")


def test_parse_rejects_unexpected_fields() -> None:
    with pytest.raises(LLMOutputParseError):
        parse_llm_output(_payload(extra_field="nope"))


def test_valid_citations() -> None:
    output = parse_llm_output(_payload())
    validated = validate_llm_citations(output, evidence_count=1)
    assert len(validated) == 1


def test_missing_citation_for_marker() -> None:
    output = parse_llm_output(_payload(citations=[]))
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=1)


def test_rank_outside_range() -> None:
    output = parse_llm_output(_payload(citations=[{"marker": 1, "evidence_rank": 9}]))
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=1)


def test_marker_rank_mismatch() -> None:
    output = parse_llm_output(_payload(citations=[{"marker": 1, "evidence_rank": 2}]))
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=2)


def test_duplicate_markers_collapse() -> None:
    output = parse_llm_output(
        _payload(
            answer="Same [1] and again [1].",
            citations=[
                {"marker": 1, "evidence_rank": 1},
                {"marker": 1, "evidence_rank": 1},
            ],
        )
    )
    validated = validate_llm_citations(output, evidence_count=1)
    assert len(validated) == 1


def test_unused_citations_dropped() -> None:
    output = parse_llm_output(
        _payload(
            answer="Only one [1].",
            citations=[
                {"marker": 1, "evidence_rank": 1},
                {"marker": 2, "evidence_rank": 2},
            ],
        )
    )
    validated = validate_llm_citations(output, evidence_count=2)
    assert [item.marker for item in validated] == [1]


def test_insufficient_evidence_allows_no_citations() -> None:
    output = parse_llm_output(
        _payload(
            answer="Not enough information.",
            insufficient_evidence=True,
            citations=[],
        )
    )
    assert validate_llm_citations(output, evidence_count=1) == []


def test_requires_citation_when_not_insufficient() -> None:
    output = parse_llm_output(
        _payload(
            answer="Plain answer without markers.",
            insufficient_evidence=False,
            citations=[],
        )
    )
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=1)


def test_build_public_citations() -> None:
    output = parse_llm_output(_payload())
    validated = validate_llm_citations(output, evidence_count=1)
    public = build_public_citations(validated, [_evidence()])
    assert public[0].document_title == "Constitution"
    assert public[0].citation_ref == "Article 14"


def test_year_brackets_are_not_citation_markers() -> None:
    output = parse_llm_output(
        _payload(
            answer="The 2023 amendment discussed in [2024] is not in evidence.",
            insufficient_evidence=True,
            citations=[],
        )
    )
    assert validate_llm_citations(output, evidence_count=2) == []


def test_section_bracket_one_is_a_citation_marker() -> None:
    output = parse_llm_output(
        _payload(
            answer="Section [1] provides equality.",
            citations=[{"marker": 1, "evidence_rank": 1}],
        )
    )
    validated = validate_llm_citations(output, evidence_count=1)
    assert [item.marker for item in validated] == [1]


def test_unused_citations_do_not_satisfy_required_citation() -> None:
    output = parse_llm_output(
        _payload(
            answer="Equality applies.",
            insufficient_evidence=False,
            citations=[{"marker": 1, "evidence_rank": 1}],
        )
    )
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=1)


def test_empty_answer_rejected_when_not_insufficient() -> None:
    output = parse_llm_output(
        _payload(
            answer="",
            insufficient_evidence=False,
            citations=[{"marker": 1, "evidence_rank": 1}],
        )
    )
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=1)


def test_empty_answer_allowed_when_insufficient() -> None:
    output = parse_llm_output(
        _payload(
            answer="",
            insufficient_evidence=True,
            citations=[],
        )
    )
    assert validate_llm_citations(output, evidence_count=1) == []
