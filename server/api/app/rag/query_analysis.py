"""Structured Legal Query Analysis module (Phase 14 + Phase 15 Temporal Extension).

Analyzes natural-language legal questions to extract normalized entities,
canonical articles, acts, sections, judgments, doctrines, intent, graph depth,
and temporal intent/dates/operators.
"""

from __future__ import annotations

import re
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from app.graph.extraction import (
    extract_entities,
    _ARTICLE,
    _SECTION,
    _CANONICAL_ACTS,
    _DOCTRINE,
    _JUDGMENT_NAMES,
    _AMENDMENT,
)

RetrievalIntent = Literal[
    "constitutional_law",
    "statutory_interpretation",
    "case_law_precedent",
    "constitutional_statutory_relationship",
    "general_legal_query",
]

TemporalOperator = Literal[
    "BEFORE",
    "AFTER",
    "SINCE",
    "UNTIL",
    "AS_OF",
    "HISTORICAL",
    "CURRENT_LAW",
]


class QueryAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_query: str
    normalized_query: str
    detected_entities: list[dict[str, Any]]
    candidate_articles: list[str]
    candidate_acts: list[str]
    candidate_sections: list[str]
    candidate_judgments: list[str]
    candidate_doctrines: list[str]
    temporal_hints: list[str]
    retrieval_intent: RetrievalIntent
    query_complexity: Literal["simple", "moderate", "complex"]
    suggested_graph_depth: int = Field(ge=1, le=5)
    subqueries: list[str] = Field(default_factory=list)

    # Phase 15 Temporal Extensions
    is_temporal: bool = False
    target_date: str | None = None
    target_year: int | None = None
    date_range: dict[str, int | None] | None = None
    temporal_operator: TemporalOperator = "CURRENT_LAW"
    referenced_amendment: str | None = None
    temporal_intent: str = "current_law"


def normalize_query_text(query: str) -> str:
    """Clean and normalize spaces and punctuation in legal query."""
    text = " ".join(query.strip().split())
    return text


def extract_temporal_analysis(text: str) -> dict[str, Any]:
    """Detect temporal expressions, operators, dates, and amendment references."""
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    target_year = years[0] if years else None
    target_date = str(target_year) if target_year else None

    amd_match = _AMENDMENT.search(text)
    ref_amendment = None
    if amd_match:
        num = amd_match.group(1) or amd_match.group(2) or amd_match.group(0)
        num_clean = re.sub(r"\D+", "", str(num))
        if num_clean:
            ref_amendment = f"{num_clean}th Constitutional Amendment"
            if not target_year:
                if num_clean == "44":
                    target_year = 1978
                    target_date = "1978"
                elif num_clean == "42":
                    target_year = 1976
                    target_date = "1976"

    operator: TemporalOperator = "CURRENT_LAW"
    is_temporal = False
    intent_label = "current_law"

    if re.search(r"\bbefore\b|\bprior to\b|\bpre-\b", text, re.I):
        operator = "BEFORE"
        is_temporal = True
        intent_label = "historical_pre_amendment"
    elif re.search(r"\bafter\b|\bfollowing\b|\bpost-\b|\bsince\b", text, re.I):
        operator = "AFTER"
        is_temporal = True
        intent_label = "post_amendment_development"
    elif re.search(r"\bin 19\d{2}\b|\bin 20\d{2}\b|\bas of\b|\bat the time\b|\bwas in force\b", text, re.I):
        operator = "AS_OF"
        is_temporal = True
        intent_label = "historical_point_in_time"
    elif re.search(r"\bhistory\b|\bevolution\b|\bevolved\b|\bhistorically\b|\boriginally\b", text, re.I):
        operator = "HISTORICAL"
        is_temporal = True
        intent_label = "historical_evolution"
    elif target_year or ref_amendment:
        is_temporal = True
        operator = "AS_OF"
        intent_label = "point_in_time"

    date_range = None
    if len(years) >= 2:
        date_range = {"start": min(years), "end": max(years)}

    return {
        "is_temporal": is_temporal,
        "target_date": target_date,
        "target_year": target_year,
        "date_range": date_range,
        "temporal_operator": operator,
        "referenced_amendment": ref_amendment,
        "temporal_intent": intent_label,
    }


def extract_temporal_hints(text: str) -> list[str]:
    """Extract year numbers or temporal expressions from query."""
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    hints = [f"year:{y}" for y in years]
    if re.search(r"\bamendment\b", text, re.I):
        hints.append("amendment")
    if re.search(r"\bevolved|evolution|history|over time|changed\b", text, re.I):
        hints.append("historical_evolution")
    return sorted(set(hints))


def infer_retrieval_intent(
    has_articles: bool,
    has_sections: bool,
    has_acts: bool,
    has_judgments: bool,
    has_doctrines: bool,
    selected_mode: str | None = None,
) -> RetrievalIntent:
    """Infer intent from entities and user research mode preference."""
    if selected_mode == "CONSTITUTIONAL":
        return "constitutional_law"
    if selected_mode == "STATUTORY":
        return "statutory_interpretation"
    if selected_mode == "CASE_LAW":
        return "case_law_precedent"

    if (has_articles or has_doctrines) and (has_sections or has_acts):
        return "constitutional_statutory_relationship"
    if has_articles or has_doctrines:
        return "constitutional_law"
    if has_sections or has_acts:
        return "statutory_interpretation"
    if has_judgments:
        return "case_law_precedent"

    return "general_legal_query"


def generate_subqueries(query: str, intent: RetrievalIntent, entities: list[dict[str, Any]]) -> list[str]:
    """Generate subqueries for complex queries to improve evidence coverage."""
    subqueries: list[str] = []

    art_names = [e["name"] for e in entities if e["label"] == "Article"]
    sec_names = [e["name"] for e in entities if e["label"] == "Section"]
    act_names = [e["name"] for e in entities if e["label"] == "Act"]
    judg_names = [e["name"] for e in entities if e["label"] == "Judgment"]
    doc_names = [e["name"] for e in entities if e["label"] == "Doctrine"]

    if art_names and (sec_names or act_names):
        subqueries.append(f"What is the scope of {art_names[0]}?")
        target_statute = sec_names[0] if sec_names else act_names[0]
        subqueries.append(f"What does {target_statute} provide?")
        subqueries.append(f"Supreme Court rulings on {target_statute} and {art_names[0]}")
    elif art_names and judg_names:
        subqueries.append(f"What is established under {art_names[0]}?")
        subqueries.append(f"How did {judg_names[0]} interpret {art_names[0]}?")
    elif sec_names and judg_names:
        subqueries.append(f"What does {sec_names[0]} mandate?")
        subqueries.append(f"How did {judg_names[0]} rule on {sec_names[0]}?")
    elif len(art_names) >= 2:
        subqueries.append(f"Scope of {art_names[0]}")
        subqueries.append(f"Scope of {art_names[1]}")
    elif doc_names:
        subqueries.append(f"Definition and origin of {doc_names[0]}")
        subqueries.append(f"Supreme Court decisions on {doc_names[0]}")

    return subqueries


def analyze_query(query: str, mode: str | None = None) -> QueryAnalysisResult:
    """Run structured query analysis on a natural language legal question."""
    normalized = normalize_query_text(query)
    extracted = extract_entities(normalized)

    entities_list = [
        {"id": e.id, "label": e.label, "name": e.name, "confidence": e.confidence}
        for e in extracted
    ]

    candidate_articles = sorted({e.name for e in extracted if e.label == "Article"})
    candidate_acts = sorted({e.name for e in extracted if e.label == "Act"})
    candidate_sections = sorted({e.name for e in extracted if e.label == "Section"})
    candidate_judgments = sorted({e.name for e in extracted if e.label == "Judgment"})
    candidate_doctrines = sorted({e.name for e in extracted if e.label == "Doctrine"})

    temporal_hints = extract_temporal_hints(normalized)
    temp_analysis = extract_temporal_analysis(normalized)

    intent = infer_retrieval_intent(
        has_articles=bool(candidate_articles),
        has_sections=bool(candidate_sections),
        has_acts=bool(candidate_acts),
        has_judgments=bool(candidate_judgments),
        has_doctrines=bool(candidate_doctrines),
        selected_mode=mode,
    )

    entity_count = len(extracted)
    word_count = len(normalized.split())

    if entity_count >= 2 or intent == "constitutional_statutory_relationship" or word_count > 15 or temp_analysis["is_temporal"]:
        complexity = "complex"
        suggested_depth = 3
    elif entity_count == 1 or word_count > 8:
        complexity = "moderate"
        suggested_depth = 2
    else:
        complexity = "simple"
        suggested_depth = 2

    subqueries = generate_subqueries(normalized, intent, entities_list)

    return QueryAnalysisResult(
        original_query=query,
        normalized_query=normalized,
        detected_entities=entities_list,
        candidate_articles=candidate_articles,
        candidate_acts=candidate_acts,
        candidate_sections=candidate_sections,
        candidate_judgments=candidate_judgments,
        candidate_doctrines=candidate_doctrines,
        temporal_hints=temporal_hints,
        retrieval_intent=intent,
        query_complexity=complexity,
        suggested_graph_depth=suggested_depth,
        subqueries=subqueries,
        is_temporal=temp_analysis["is_temporal"],
        target_date=temp_analysis["target_date"],
        target_year=temp_analysis["target_year"],
        date_range=temp_analysis["date_range"],
        temporal_operator=temp_analysis["temporal_operator"],
        referenced_amendment=temp_analysis["referenced_amendment"],
        temporal_intent=temp_analysis["temporal_intent"],
    )
