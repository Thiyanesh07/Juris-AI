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


# ============================================================
# JAI-003 & JAI-004 Regression Tests
# ============================================================

def test_grouped_citations_bracket_syntax() -> None:
    """JAI-003: Grouped markers like [1, 2, 3], [1,2,3,5], [1; 2], [1-3] must be recognized."""
    output = parse_llm_output(
        _payload(
            answer="Provisions apply [1, 2, 3] and also [4-5].",
            citations=[
                {"marker": 1, "evidence_rank": 1},
                {"marker": 2, "evidence_rank": 2},
                {"marker": 3, "evidence_rank": 3},
                {"marker": 4, "evidence_rank": 4},
                {"marker": 5, "evidence_rank": 5},
            ],
        )
    )
    validated = validate_llm_citations(output, evidence_count=5)
    markers = [item.marker for item in validated]
    assert markers == [1, 2, 3, 4, 5]


def test_grouped_citations_with_semicolon_and_no_spaces() -> None:
    """JAI-003: Grouped markers with semicolons or no spaces [1,2,3,5]."""
    output = parse_llm_output(
        _payload(
            answer="Refer to authorities [1,2,3,5] and [4; 6].",
            citations=[
                {"marker": 1, "evidence_rank": 1},
                {"marker": 2, "evidence_rank": 2},
                {"marker": 3, "evidence_rank": 3},
                {"marker": 4, "evidence_rank": 4},
                {"marker": 5, "evidence_rank": 5},
                {"marker": 6, "evidence_rank": 6},
            ],
        )
    )
    validated = validate_llm_citations(output, evidence_count=6)
    assert [item.marker for item in validated] == [1, 2, 3, 4, 5, 6]


def test_grouped_citations_out_of_range_raises_validation_error() -> None:
    """JAI-003: Grouped marker referencing an out-of-range index must raise CitationValidationError."""
    output = parse_llm_output(
        _payload(
            answer="Invalid group [1, 5] when only 2 chunks exist.",
            citations=[
                {"marker": 1, "evidence_rank": 1},
            ],
        )
    )
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=2)


def test_missing_citation_in_group_raises_validation_error() -> None:
    """JAI-003: When text has [1, 2] but LLM omitted marker 2 from citations array, it must raise CitationValidationError."""
    output = parse_llm_output(
        _payload(
            answer="Both provisions apply [1, 2].",
            citations=[{"marker": 1, "evidence_rank": 1}],
        )
    )
    with pytest.raises(CitationValidationError):
        validate_llm_citations(output, evidence_count=2)


def test_duplicate_chunks_from_same_document() -> None:
    """JAI-003: Multiple chunks from the same document maintain independent ranks and public citation mapping."""
    doc_id = UUID("00000000-0000-0000-0000-000000000010")
    ev1 = _evidence(rank=1)
    ev2 = HybridEvidence.model_validate(
        {
            **ev1.model_dump(),
            "rank": 2,
            "chunk_id": UUID("00000000-0000-0000-0000-000000000002"),
            "chunk_index": 1,
            "citation_ref": "Article 15",
            "page_start": 2,
            "page_end": 2,
        }
    )
    output = parse_llm_output(
        _payload(
            answer="Both articles apply [1] and [2].",
            citations=[
                {"marker": 1, "evidence_rank": 1},
                {"marker": 2, "evidence_rank": 2},
            ],
        )
    )
    validated = validate_llm_citations(output, evidence_count=2)
    public = build_public_citations(validated, [ev1, ev2])
    assert len(public) == 2
    assert public[0].citation_ref == "Article 14"
    assert public[1].citation_ref == "Article 15"
    assert public[0].chunk_id != public[1].chunk_id


def test_groundedness_validation_truthful_status() -> None:
    """JAI-004: validate_response_groundedness must never treat 0 verified citations as grounded."""
    from app.rag.citation_verifier import VerifiedCitation
    from app.rag.query_analysis import analyze_query
    from app.rag.validation import validate_response_groundedness

    qa_res = analyze_query("What is Article 21?")

    # 1. Empty citations -> grounded MUST be False
    rep_empty = validate_response_groundedness(
        answer="Some answer text without citations.",
        citations=[],
        query_analysis=qa_res,
        insufficient_evidence=False,
    )
    assert rep_empty.grounded is False
    assert rep_empty.citation_valid is False
    assert rep_empty.verified_count == 0

    # 2. Insufficient evidence -> grounded MUST be False even if answer string exists
    rep_insufficient = validate_response_groundedness(
        answer="Insufficient evidence to answer.",
        citations=[],
        query_analysis=qa_res,
        insufficient_evidence=True,
    )
    assert rep_insufficient.grounded is False
    assert rep_insufficient.citation_valid is False

    # 3. Unverified citations present -> grounded MUST be False
    unverified_cit = VerifiedCitation(
        marker=1,
        citation_text="Sec 1",
        source_chunk_id="chk1",
        source_document_id="doc1",
        source_document_title="Title",
        verification_status="UNVERIFIED",
        confidence=0.0,
        provenance_intact=False,
    )
    rep_unverified = validate_response_groundedness(
        answer="Answer with unverified citation [1].",
        citations=[unverified_cit],
        query_analysis=qa_res,
        insufficient_evidence=False,
    )
    assert rep_unverified.grounded is False
    assert rep_unverified.citation_valid is False
    assert rep_unverified.unverified_count == 1

    # 4. All citations verified and matching text markers -> grounded is True
    verified_cit = VerifiedCitation(
        marker=1,
        citation_text="Sec 1",
        source_chunk_id="chk1",
        source_document_id="doc1",
        source_document_title="Title",
        verification_status="VERIFIED",
        confidence=1.0,
        provenance_intact=True,
    )
    rep_verified = validate_response_groundedness(
        answer="Answer with verified citation [1].",
        citations=[verified_cit],
        query_analysis=qa_res,
        insufficient_evidence=False,
    )
    assert rep_verified.grounded is True
    assert rep_verified.citation_valid is True
    assert rep_verified.verified_count == 1
    assert rep_verified.unverified_count == 0


def test_correct_inline_markers_and_matching_metadata() -> None:
    """Valid inline markers matching structured metadata are accepted."""
    output = parse_llm_output(
        json.dumps({
            "answer": "Equality applies under Article 14 [1]. Liberty is protected under Article 21 [2].",
            "insufficient_evidence": False,
            "citations": [
                {"marker": 1, "evidence_rank": 1},
                {"marker": 2, "evidence_rank": 2},
            ],
        })
    )
    validated = validate_llm_citations(output, evidence_count=2)
    assert len(validated) == 2
    assert validated[0].marker == 1
    assert validated[1].marker == 2


def test_missing_inline_markers_raises_descriptive_error() -> None:
    """When citations exist but no inline markers appear in answer text, raises descriptive error."""
    output = parse_llm_output(
        json.dumps({
            "answer": "Equality applies under Article 14 and personal liberty is protected under Article 21.",
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        })
    )
    with pytest.raises(CitationValidationError) as exc_info:
        validate_llm_citations(output, evidence_count=2)
    assert "Missing inline citation markers in answer text" in str(exc_info.value)
    assert "[1]" in str(exc_info.value)


def test_marker_referencing_nonexistent_evidence() -> None:
    """A citation marker referencing an evidence rank beyond available evidence is rejected."""
    output = parse_llm_output(
        json.dumps({
            "answer": "Claim supported by out of bounds authority [99].",
            "insufficient_evidence": False,
            "citations": [{"marker": 99, "evidence_rank": 99}],
        })
    )
    with pytest.raises(CitationValidationError) as exc_info:
        validate_llm_citations(output, evidence_count=5)
    assert "out of range" in str(exc_info.value)


def test_structured_metadata_disagreeing_with_inline_markers() -> None:
    """Mismatches between inline text markers and structured citations array are rejected."""
    # Case A: Answer references marker [2] but citations only includes marker 1
    output_missing_citation = parse_llm_output(
        json.dumps({
            "answer": "Claim with marker [1] and another claim with [2].",
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        })
    )
    with pytest.raises(CitationValidationError, match=r"Missing citation for marker \[2\]"):
        validate_llm_citations(output_missing_citation, evidence_count=3)

    # Case B: Citation object has marker != evidence_rank
    output_mismatched_rank = parse_llm_output(
        json.dumps({
            "answer": "Claim with marker [1].",
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 2}],
        })
    )
    with pytest.raises(CitationValidationError, match="Citation marker must equal evidence_rank"):
        validate_llm_citations(output_mismatched_rank, evidence_count=3)


def test_multiple_claims_requiring_separate_citations() -> None:
    """Multiple distinct claims in complex answers are correctly parsed and validated."""
    output = parse_llm_output(
        json.dumps({
            "answer": (
                "Article 14 establishes equality before law [1]. "
                "Article 19 protects fundamental freedoms [2]. "
                "Articles 14, 19 and 21 form the golden triangle [1, 2, 3]."
            ),
            "insufficient_evidence": False,
            "citations": [
                {"marker": 1, "evidence_rank": 1},
                {"marker": 2, "evidence_rank": 2},
                {"marker": 3, "evidence_rank": 3},
            ],
        })
    )
    validated = validate_llm_citations(output, evidence_count=3)
    assert len(validated) == 3
    assert [v.marker for v in validated] == [1, 2, 3]


def test_partial_evidence_and_insufficient_evidence_abstention() -> None:
    """When evidence is insufficient or partial, abstention is preserved without false grounding."""
    # 1. Output declaring insufficient_evidence=True with explanation
    output = parse_llm_output(
        json.dumps({
            "answer": "The provided legal authorities do not contain information on this topic.",
            "insufficient_evidence": True,
            "citations": [],
        })
    )
    validated = validate_llm_citations(output, evidence_count=5)
    assert validated == []

    # 2. Grounding validator confirms grounded is False
    from app.rag.query_analysis import analyze_query
    from app.rag.validation import validate_response_groundedness

    qa_res = analyze_query("Out of corpus question")
    rep = validate_response_groundedness(
        answer=output.answer,
        citations=[],
        query_analysis=qa_res,
        insufficient_evidence=True,
    )
    assert rep.grounded is False
    assert rep.citation_valid is False
