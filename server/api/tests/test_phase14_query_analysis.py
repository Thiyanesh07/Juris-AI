"""Phase 14 Unit tests for Structured Query Analysis module."""

from __future__ import annotations

import pytest

from app.rag.query_analysis import (
    analyze_query,
    extract_temporal_hints,
    infer_retrieval_intent,
    normalize_query_text,
)


def test_normalize_query_text() -> None:
    raw = "  What is   the scope of   Article 19 ?  "
    normalized = normalize_query_text(raw)
    assert normalized == "What is the scope of Article 19 ?"


def test_extract_temporal_hints() -> None:
    text = "How did the 1973 CrPC amendment change after 2023 ?"
    hints = extract_temporal_hints(text)
    assert "year:1973" in hints
    assert "year:2023" in hints
    assert "amendment" in hints


def test_infer_retrieval_intent() -> None:
    intent1 = infer_retrieval_intent(
        has_articles=True,
        has_sections=False,
        has_acts=False,
        has_judgments=False,
        has_doctrines=False,
    )
    assert intent1 == "constitutional_law"

    intent2 = infer_retrieval_intent(
        has_articles=True,
        has_sections=True,
        has_acts=True,
        has_judgments=False,
        has_doctrines=False,
    )
    assert intent2 == "constitutional_statutory_relationship"

    intent3 = infer_retrieval_intent(
        has_articles=False,
        has_sections=True,
        has_acts=True,
        has_judgments=False,
        has_doctrines=False,
        selected_mode="STATUTORY",
    )
    assert intent3 == "statutory_interpretation"


def test_analyze_query_section_and_article() -> None:
    query = "What is the relationship between Section 66A of the IT Act and freedom of speech under Article 19?"
    res = analyze_query(query)

    assert "Article 19" in res.candidate_articles
    assert "Section 66A" in res.candidate_sections
    assert res.retrieval_intent == "constitutional_statutory_relationship"
    assert res.query_complexity == "complex"
    assert res.suggested_graph_depth == 3
    assert len(res.subqueries) >= 2


def test_analyze_query_judgment_and_article() -> None:
    query = "How did Maneka Gandhi change the interpretation of Article 21?"
    res = analyze_query(query)

    assert "Article 21" in res.candidate_articles
    assert "Maneka Gandhi" in res.candidate_judgments
    assert res.retrieval_intent == "constitutional_law"
    assert res.query_complexity == "complex"
