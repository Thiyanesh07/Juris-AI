"""Hybrid Evidence Fusion & Mode-based Filtering Module (Phase 14).

Combines FAISS vector retrieval candidates with Neo4j graph traversal candidates.
Applies normalized scoring, mode-specific evidence weighting/filtering,
deduplication, and provenance verification.
"""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.core.config import Settings
from app.schemas.hybrid import HybridEvidence, HybridGraphContext, HybridGraphEntityContext

RetrievalStrategy = Literal["hybrid", "vector_only", "graph_only"]
ResearchMode = Literal["COMPREHENSIVE", "CONSTITUTIONAL", "STATUTORY", "CASE_LAW"]


def clamp_score(val: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, val))


def boost_score_by_mode(
    raw_score: float,
    doc_type: str,
    doc_title: str,
    hierarchy: dict[str, Any],
    mode: ResearchMode,
) -> float:
    """Adjust score slightly according to Research Mode preference."""
    boost = 1.0
    doc_type_upper = doc_type.upper()
    title_lower = doc_title.lower()

    if mode == "CONSTITUTIONAL":
        if "constitution" in title_lower or doc_type_upper == "CONSTITUTION" or "article" in str(hierarchy).lower():
            boost = 1.25
        elif "judgment" in title_lower or doc_type_upper == "JUDGMENT":
            boost = 1.10
        else:
            boost = 0.85
    elif mode == "STATUTORY":
        if "act" in title_lower or "code" in title_lower or "sanhita" in title_lower or doc_type_upper in ("ACT", "ORDINANCE", "RULE"):
            boost = 1.25
        elif "judgment" in title_lower:
            boost = 1.05
        else:
            boost = 0.90
    elif mode == "CASE_LAW":
        if "judgment" in title_lower or doc_type_upper == "JUDGMENT" or "v." in title_lower or "vs." in title_lower:
            boost = 1.30
        else:
            boost = 0.85

    return clamp_score(raw_score * boost, 0.0, 1.0)


def calculate_entity_boost(
    doc_title: str,
    citation_ref: str,
    hierarchy: dict[str, Any],
    detected_entities: list[dict[str, Any]],
    text: str = "",
) -> float:
    """Calculate generic entity relevance boost based on metadata and text matching detected query entities."""
    if not detected_entities:
        return 1.0

    title_lower = doc_title.lower().strip()
    cite_lower = (citation_ref or "").lower().strip()
    hier_str = str(hierarchy or {}).lower()
    text_lower = (text or "").lower()

    boost = 1.0
    matched_entity_ids: set[str] = set()

    for entity in detected_entities:
        name = str(entity.get("name", "")).strip().lower()
        if not name or len(name) < 3:
            continue
        entity_id = str(entity.get("id", ""))
        label = str(entity.get("label", "")).lower()

        # Check title match (case law title, statute name)
        if name in title_lower or (len(title_lower) >= 5 and title_lower in name):
            if entity_id not in matched_entity_ids:
                matched_entity_ids.add(entity_id)
                if label in ("judgment", "act"):
                    boost *= 1.35
                else:
                    boost *= 1.25
            continue

        # Check citation reference match (e.g. "Article 21", "Section 302", "1978 AIR 597")
        if cite_lower and (name in cite_lower or (len(cite_lower) >= 4 and cite_lower in name)):
            if entity_id not in matched_entity_ids:
                matched_entity_ids.add(entity_id)
                boost *= 1.20
            continue

        # Check amendment match (e.g. 44th / forty-fourth)
        if label == "amendment":
            num = "".join(filter(str.isdigit, name))
            ord_map = {"44": "forty-fourth", "42": "forty-second", "101": "one hundred and first", "73": "seventy-third"}
            word_ord = ord_map.get(num, "")
            if (num and (f"{num}th" in title_lower or f"{num}th" in cite_lower or f"{num}th" in text_lower)) or \
               (word_ord and (word_ord in title_lower or word_ord in cite_lower or word_ord in text_lower)):
                if entity_id not in matched_entity_ids:
                    matched_entity_ids.add(entity_id)
                    boost *= 1.35
                continue

        # Check hierarchy match (e.g. hierarchy has article: "21" or section: "437")
        if label == "article":
            art_num = "".join(filter(str.isdigit, name))
            if art_num and (art_num in hier_str or f"article {art_num}" in cite_lower or f"article {art_num}" in text_lower):
                if entity_id not in matched_entity_ids:
                    matched_entity_ids.add(entity_id)
                    boost *= 1.15
                continue
        elif label == "section":
            sec_num = "".join(filter(str.isdigit, name))
            if sec_num and (sec_num in hier_str or f"section {sec_num}" in cite_lower or f"section {sec_num}" in text_lower):
                if entity_id not in matched_entity_ids:
                    matched_entity_ids.add(entity_id)
                    boost *= 1.15
                continue

        # Check text match for specific named judgments or acts
        if text_lower and label in ("judgment", "act") and name in text_lower:
            if entity_id not in matched_entity_ids:
                matched_entity_ids.add(entity_id)
                boost *= 1.15

    return min(1.50, boost)


def fuse_and_rank_evidence(
    dense_candidates: list[dict[str, Any]],
    graph_candidate_chunks: dict[str, dict[str, Any]],
    all_chunks_by_id: dict[str, dict[str, Any]],
    strategy: RetrievalStrategy = "hybrid",
    mode: ResearchMode = "COMPREHENSIVE",
    top_k: int = 10,
    vector_weight: float = 0.50,
    graph_weight: float = 0.50,
    detected_entities: list[dict[str, Any]] | None = None,
) -> list[HybridEvidence]:
    """Fuse FAISS vector candidates and Neo4j graph candidates into ranked HybridEvidence."""
    candidate_states: dict[str, dict[str, Any]] = {}

    # 1. Process Dense Vector Candidates
    if strategy in ("hybrid", "vector_only"):
        for rank, hit in enumerate(dense_candidates, start=1):
            cid = str(hit["chunk_id"])
            dense_score = float(hit.get("score", 0.0))
            candidate_states[cid] = {
                "chunk_id": cid,
                "dense_score": dense_score,
                "dense_rank": rank,
                "dense_matched": True,
                "graph_score": 0.0,
                "graph_rank": None,
                "graph_context": None,
                "sources": ["dense"],
            }

    # 2. Process Graph Candidates
    if strategy in ("hybrid", "graph_only"):
        for cid, g_info in graph_candidate_chunks.items():
            graph_score = float(g_info.get("graph_score", 0.60))
            graph_context_data = g_info.get("graph_context")

            if cid in candidate_states:
                st = candidate_states[cid]
                st["graph_score"] = graph_score
                st["graph_context"] = graph_context_data
                if "graph" not in st["sources"]:
                    st["sources"].append("graph")
            else:
                candidate_states[cid] = {
                    "chunk_id": cid,
                    "dense_score": 0.0,
                    "dense_rank": None,
                    "dense_matched": False,
                    "graph_score": graph_score,
                    "graph_rank": None,
                    "graph_context": graph_context_data,
                    "sources": ["graph"],
                }

    # Assign graph ranks
    graph_ranked = sorted(
        [st for st in candidate_states.values() if st["graph_score"] > 0],
        key=lambda item: (-item["graph_score"], item["chunk_id"]),
    )
    for grank, st in enumerate(graph_ranked, start=1):
        st["graph_rank"] = grank

    # Compute hybrid scores & mode boosts
    processed_list: list[dict[str, Any]] = []
    for st in candidate_states.values():
        v_score = clamp_score(st["dense_score"], 0.0, 1.0)
        g_score = clamp_score(st["graph_score"], 0.0, 1.0)

        if strategy == "vector_only":
            h_score = v_score
        elif strategy == "graph_only":
            h_score = g_score
        else:
            h_score = (vector_weight * v_score) + (graph_weight * g_score)

        # Lookup chunk row for document metadata
        cid = st["chunk_id"]
        chunk_row = all_chunks_by_id.get(cid, {})

        doc_type = str(chunk_row.get("document_type") or chunk_row.get("type") or "")
        doc_title = str(chunk_row.get("document_title") or chunk_row.get("title") or "")
        hierarchy = chunk_row.get("hierarchy") or {}
        citation_ref = str(chunk_row.get("citation_ref") or "")
        chunk_text = str(chunk_row.get("text") or "")

        mode_boosted = boost_score_by_mode(h_score, doc_type, doc_title, hierarchy, mode)
        entity_boost = calculate_entity_boost(doc_title, citation_ref, hierarchy, detected_entities or [], text=chunk_text)
        unclamped_score = mode_boosted * entity_boost
        final_hybrid_score = clamp_score(unclamped_score, 0.0, 1.0)

        processed_list.append({
            **st,
            "unclamped_score": unclamped_score,
            "hybrid_score": final_hybrid_score,
            "raw_row": chunk_row,
        })

    # Sort candidates by unclamped boosted score first to preserve exact entity boosts and avoid flat 1.0 plateaus
    ordered = sorted(
        processed_list,
        key=lambda item: (-item["unclamped_score"], -item["dense_score"], -item["graph_score"], item["chunk_id"]),
    )

    # Deduplicate nearly identical chunks from same page/document if top_k is tight
    final_evidence: list[HybridEvidence] = []
    doc_chunk_count: dict[str, int] = {}

    for rank_idx, item in enumerate(ordered, start=1):
        row = item["raw_row"]
        if not row:
            continue

        cid = item["chunk_id"]
        doc_id = str(row.get("document_id"))
        page_start = row.get("page_start")

        # Diversification rule: max 2 chunks per document in top_k unless candidate pool is smaller
        if doc_chunk_count.get(doc_id, 0) >= 2 and len(final_evidence) + (len(ordered) - rank_idx) >= top_k:
            continue
        doc_chunk_count[doc_id] = doc_chunk_count.get(doc_id, 0) + 1

        if len(final_evidence) >= top_k:
            break

        g_ctx = None
        if item["graph_context"]:
            entities = [
                HybridGraphEntityContext(
                    id=e["id"],
                    label=e.get("label", "Concept"),
                    name=e.get("name", e["id"]),
                )
                for e in item["graph_context"].get("entities", [])
            ]
            g_ctx = HybridGraphContext(
                hops=item["graph_context"].get("hops", 2),
                seed_chunk_ids=item["graph_context"].get("seed_chunk_ids", []),
                entities=entities,
            )

        pdf_url = row.get("pdf_url") or (f"/api/v1/documents/{doc_id}/pdf" if doc_id else None)

        evidence_obj = HybridEvidence(
            rank=len(final_evidence) + 1,
            chunk_id=UUID(cid),
            document_id=UUID(doc_id),
            document_title=str(row.get("document_title") or "Legal Document"),
            document_version_id=UUID(row["document_version_id"]) if row.get("document_version_id") else None,
            chunk_index=int(row.get("chunk_index", 0)),
            text=str(row.get("text", "")),
            page_start=page_start,
            page_end=row.get("page_end"),
            hierarchy=row.get("hierarchy") or {},
            citation_ref=row.get("citation_ref"),
            source_url=row.get("source_url"),
            pdf_url=pdf_url,
            dense_score=item["dense_score"],
            graph_score=item["graph_score"],
            hybrid_score=item["hybrid_score"],
            dense_rank=item["dense_rank"],
            graph_rank=item["graph_rank"],
            dense_matched=item["dense_matched"],
            evidence_sources=item["sources"],
            graph_context=g_ctx,
            score_type="Calibrated Fusion Score" if strategy == "hybrid" else ("Vector Cosine Similarity" if strategy == "vector_only" else "Graph Traversal Score"),
            verification_status="UNVERIFIED",
        )

        final_evidence.append(evidence_obj)

    return final_evidence


class EvidenceSufficiencyAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["STRONG", "PARTIAL", "AUTHORITY_ABSENT", "NO_EVIDENCE"]
    is_sufficient: bool
    missing_authorities: list[str] = Field(default_factory=list)
    gap_type: Literal["corpus_document", "graph_entities", "graph_relationships", "metadata", "none"] = "none"
    explanation: str = ""
    rejection_reason: str | None = None


def assess_evidence_sufficiency(
    fused_evidence: list[HybridEvidence],
    detected_entities: list[dict[str, Any]],
    query_text: str = "",
) -> EvidenceSufficiencyAssessment:
    """Evaluate evidence sufficiency and identify missing authorities and gap types."""
    if not fused_evidence:
        return EvidenceSufficiencyAssessment(
            state="NO_EVIDENCE",
            is_sufficient=False,
            missing_authorities=[str(e.get("name", "")) for e in (detected_entities or []) if e.get("name")],
            gap_type="corpus_document",
            explanation="No candidate evidence chunks were retrieved from the indexed corpus.",
            rejection_reason="no_candidates_retrieved",
        )

    domain_entities = [
        e for e in (detected_entities or [])
        if e.get("label") in ("Act", "Section", "Article", "Judgment", "Constitution", "Amendment", "Doctrine")
    ]

    matched_entity_names: set[str] = set()
    unmatched_entity_names: list[str] = []

    for ent in domain_entities:
        ename = str(ent.get("name", "")).strip()
        if not ename or len(ename) < 3:
            continue
        ename_lower = ename.lower()
        elabel = str(ent.get("label", "")).lower()

        matched = False
        for ev in fused_evidence:
            title_lower = ev.document_title.lower()
            text_lower = ev.text.lower()
            hier_str = str(ev.hierarchy or {}).lower()
            cite_lower = (ev.citation_ref or "").lower()

            if elabel == "article":
                art_num = "".join(filter(str.isdigit, ename_lower))
                is_constitution = "constitution of india" in title_lower or "constitution" in title_lower
                cite_art = re.search(r'\b(?:article|art\.?)\s*(\d+)', cite_lower)
                cite_art_num = cite_art.group(1) if cite_art else ""

                # If citation_ref explicitly refers to a different article, skip this chunk
                if cite_art_num and art_num and cite_art_num != art_num:
                    continue

                # 1. Constitution of India chunk
                if is_constitution and (
                    cite_art_num == art_num
                    or (art_num and art_num in hier_str)
                    or re.search(rf'\barticle\s+{art_num}\b', text_lower[:300])
                    or re.search(rf'^\s*{art_num}\.\s+', text_lower)
                ):
                    matched = True
                    break

                # 2. Case / Judgment substantively analyzing this article
                if "v." in title_lower or "ltd" in title_lower or "union of india" in title_lower or "in re" in title_lower:
                    if cite_art_num == art_num or re.search(rf'\barticle\s+{art_num}\b', text_lower):
                        matched = True
                        break

                # 3. Direct match in title or citation
                if f"article {art_num}" in title_lower or (cite_art_num and cite_art_num == art_num):
                    matched = True
                    break
                continue

            elif elabel == "section":
                sec_num = "".join(filter(str.isalnum, ename_lower))
                cite_sec = re.search(r'\b(?:section|sec\.?)\s*(\w+)', cite_lower)
                cite_sec_num = cite_sec.group(1) if cite_sec else ""

                if cite_sec_num and sec_num and cite_sec_num != sec_num:
                    continue

                if (sec_num and cite_sec_num == sec_num) or (sec_num and sec_num in hier_str):
                    matched = True
                    break
                if re.search(rf'\bsection\s+{sec_num}\b', text_lower):
                    matched = True
                    break
                continue

            elif elabel == "amendment":
                num = "".join(filter(str.isdigit, ename_lower))
                ord_map = {
                    "44": "forty-fourth",
                    "42": "forty-second",
                    "101": "one hundred and first",
                    "73": "seventy-third",
                    "86": "eighty-sixth",
                }
                word_ord = ord_map.get(num, "")
                if (num and (f"{num}th" in title_lower or f"{num}th" in cite_lower)) or \
                   (word_ord and (word_ord in title_lower or word_ord in cite_lower)):
                    matched = True
                    break
                continue

            elif elabel == "constitution":
                if "constitution" in title_lower or "constitution" in text_lower:
                    matched = True
                    break
                continue

            elif elabel == "doctrine":
                if ename_lower in text_lower or ename_lower in title_lower:
                    matched = True
                    break
                continue

            # Fallback for Act, Judgment, and other general entities
            if ename_lower in title_lower or ename_lower in cite_lower or ename_lower in text_lower:
                matched = True
                break

        if matched:
            matched_entity_names.add(ename)
        else:
            unmatched_entity_names.append(ename)

    # Check for explicitly requested authority categories in the query that are absent from evidence
    q_lower = (query_text or "").lower()
    if "amendment" in q_lower:
        art_match = re.search(r'\barticle\s+(\d+[a-z]?)\b', q_lower)
        if art_match:
            target_art = art_match.group(1)
            # Check if any retrieved amendment chunk actually amends target article
            has_relevant_amendment = any(
                "amendment" in ev.document_title.lower() and (
                    f"article {target_art}" in (ev.citation_ref or "").lower() or
                    re.search(rf'\b(?:amendment of|insertion of.*|substituted for)\s+article\s+{target_art}\b', ev.text.lower()) or
                    re.search(rf'\bin article\s+{target_art}\b', ev.text.lower())
                )
                for ev in fused_evidence
            )
            if not has_relevant_amendment and f"Constitutional Amendment affecting Article {target_art.upper()}" not in unmatched_entity_names:
                unmatched_entity_names.append(f"Constitutional Amendment affecting Article {target_art.upper()}")
        else:
            has_amendment_evidence = any(
                "amendment" in ev.document_title.lower() or "amendment" in ev.text.lower()
                for ev in fused_evidence
            )
            if not has_amendment_evidence and "Constitutional Amendment" not in unmatched_entity_names:
                unmatched_entity_names.append("Constitutional Amendment")

    top_score = max((e.hybrid_score for e in fused_evidence), default=0.0)

    # 1. Authority absent: query specifically asked for an authority category (e.g. amendment) absent from corpus
    if any("amendment" in n.lower() for n in unmatched_entity_names):
        missing_names = ", ".join(f"'{n}'" for n in unmatched_entity_names[:3])
        return EvidenceSufficiencyAssessment(
            state="AUTHORITY_ABSENT",
            is_sufficient=False,
            missing_authorities=unmatched_entity_names,
            gap_type="corpus_document",
            explanation=f"Requested legal authority ({missing_names}) is not found in the currently indexed corpus.",
            rejection_reason=f"insufficient_corpus_evidence: No retrieved evidence matches requested legal authority ({missing_names})",
        )

    # 2. Domain entities detected in query
    if domain_entities:
        primary_entities = [
            e for e in domain_entities
            if e.get("label") in ("Act", "Section", "Article", "Amendment", "Judgment")
        ]
        has_primary_matched = any(
            str(e.get("name", "")).strip() in matched_entity_names
            for e in primary_entities
        )
        if primary_entities and not has_primary_matched:
            missing_names = ", ".join(f"'{n}'" for n in unmatched_entity_names[:3])
            return EvidenceSufficiencyAssessment(
                state="AUTHORITY_ABSENT",
                is_sufficient=False,
                missing_authorities=unmatched_entity_names,
                gap_type="corpus_document",
                explanation=f"Requested legal authority ({missing_names}) is not found in the currently indexed corpus.",
                rejection_reason=f"insufficient_corpus_evidence: No retrieved evidence matches requested legal subject ({missing_names})",
            )

        if len(matched_entity_names) == len(domain_entities) and not unmatched_entity_names and top_score >= 0.40:
            return EvidenceSufficiencyAssessment(
                state="STRONG",
                is_sufficient=True,
                missing_authorities=[],
                gap_type="none",
                explanation="Retrieved evidence directly verifies all requested legal entities and authorities.",
                rejection_reason=None,
            )
        elif len(matched_entity_names) > 0:
            return EvidenceSufficiencyAssessment(
                state="PARTIAL",
                is_sufficient=True,
                missing_authorities=unmatched_entity_names,
                gap_type="corpus_document",
                explanation=f"Evidence partially verifies {', '.join(sorted(matched_entity_names))}, but {', '.join(unmatched_entity_names)} could not be verified in the retrieved chunks.",
                rejection_reason=None,
            )
        else:
            missing_names = ", ".join(f"'{n}'" for n in unmatched_entity_names[:3])
            rejection = f"insufficient_corpus_evidence: No retrieved evidence matches requested legal subject ({missing_names})"
            return EvidenceSufficiencyAssessment(
                state="AUTHORITY_ABSENT",
                is_sufficient=False,
                missing_authorities=unmatched_entity_names,
                gap_type="corpus_document",
                explanation=f"Requested legal authority ({missing_names}) is not found in the currently indexed corpus.",
                rejection_reason=rejection,
            )

    # 2. Conceptual queries without detected domain entities
    if top_score >= 0.40:
        return EvidenceSufficiencyAssessment(
            state="STRONG",
            is_sufficient=True,
            missing_authorities=[],
            gap_type="none",
            explanation="Retrieved evidence satisfies minimum conceptual relevance threshold.",
            rejection_reason=None,
        )

    return EvidenceSufficiencyAssessment(
        state="NO_EVIDENCE",
        is_sufficient=False,
        missing_authorities=[],
        gap_type="corpus_document",
        explanation="All retrieved evidence chunks scored below minimum relevance threshold (0.40).",
        rejection_reason="insufficient_corpus_evidence: All retrieved evidence scores below minimum relevance threshold (0.40)",
    )


def evaluate_evidence_sufficiency(
    fused_evidence: list[HybridEvidence],
    detected_entities: list[dict[str, Any]],
    query_text: str = "",
) -> tuple[bool, str | None]:
    """Determine whether the retrieved evidence pool contains sufficient legal grounding for the query.

    Returns (is_sufficient, rejection_reason).
    """
    assessment = assess_evidence_sufficiency(fused_evidence, detected_entities, query_text)
    return assessment.is_sufficient, assessment.rejection_reason
