"""Unit tests for deterministic graph extraction (no Neo4j)."""

from __future__ import annotations

from app.graph.extraction import (
    Relation,
    contains_provenance_key,
    entity_provenance_key,
    extract_entities,
    extract_relations,
    source_fingerprint,
)


def test_article_and_section_ids_are_instrument_scoped() -> None:
    ipc_text = "Section 1 applies. Section 2 defines person."
    crpc_text = "Section 1 of the procedure."
    ipc_entities = extract_entities(ipc_text, document_title="Indian Penal Code")
    crpc_entities = extract_entities(crpc_text, document_title="Criminal Procedure Code")
    ipc_section = next(e for e in ipc_entities if e.label == "Section")
    crpc_section = next(e for e in crpc_entities if e.label == "Section")
    assert ipc_section.id == "section:indian-penal-code:1"
    assert crpc_section.id == "section:criminal-procedure-code:1"
    assert ipc_section.id != crpc_section.id


def test_article_id_extraction() -> None:
    entities = extract_entities("Article 14 guarantees equality.", document_title="Constitution")
    article = next(e for e in entities if e.label == "Article")
    assert article.id in ("article:constitution:14", "article:constitution_of_india:14")
    assert article.name == "Article 14"


def test_act_id_consistency_across_documents() -> None:
    text = "Under the Indian Penal Code Act"
    first = extract_entities(text, document_title="Doc A")
    second = extract_entities(text, document_title="Doc B")
    act_first = next(e for e in first if e.label == "Act")
    act_second = next(e for e in second if e.label == "Act")
    assert act_first.id == act_second.id
    assert act_first.id.startswith("act:")


def test_supreme_court_canonicalization() -> None:
    entities_a = extract_entities("The Supreme Court held.", document_title="A")
    entities_b = extract_entities("The Supreme Court of India held.", document_title="B")
    court_a = next(e for e in entities_a if e.label == "Court")
    court_b = next(e for e in entities_b if e.label == "Court")
    assert court_a.id == court_b.id == "court:supreme-court-of-india"


def test_distinct_high_courts_and_ignore_bare_high_court() -> None:
    text = "Bombay High Court and Delhi High Court differ. High Court alone is ignored."
    entities = extract_entities(text, document_title="Judgments")
    courts = {e.id for e in entities if e.label == "Court"}
    assert "court:bombay-high-court" in courts
    assert "court:delhi-high-court" in courts
    assert "court:high-court" not in courts
    assert len(courts) == 2


def test_concept_ids_are_instrument_scoped() -> None:
    text = 'Section 2 defines "person" for this Act.'
    ipc = extract_entities(text, document_title="Indian Penal Code")
    crpc = extract_entities(text, document_title="Criminal Procedure Code")
    ipc_concept = next(e for e in ipc if e.label == "Concept")
    crpc_concept = next(e for e in crpc if e.label == "Concept")
    assert ipc_concept.id == "concept:indian-penal-code:person"
    assert crpc_concept.id == "concept:criminal-procedure-code:person"
    assert ipc_concept.id != crpc_concept.id


def test_defines_links_nearest_preceding_provision_only() -> None:
    text = "Section 1 title. Section 2 defines person for this chapter."
    entities = extract_entities(text, document_title="Sample Act")
    relations = extract_relations(text, entities, document_title="Sample Act")
    assert all(rel.type == "DEFINES" for rel in relations)
    assert len(relations) == 1
    assert relations[0].source_id.endswith(":2")
    assert relations[0].target_id.endswith(":person")


def test_no_order_based_references() -> None:
    text = "Section 1 and Section 2 and Section 3"
    entities = extract_entities(text, document_title="Act")
    relations = extract_relations(text, entities, document_title="Act")
    assert relations == []


def test_source_fingerprint_is_stable() -> None:
    relation = Relation("section:a:1", "concept:a:person", "DEFINES", 0.9)
    first = source_fingerprint("chunk-1", relation)
    second = source_fingerprint("chunk-1", relation)
    third = source_fingerprint("chunk-2", relation)
    assert first == second
    assert first != third


def test_entity_provenance_key_is_stable() -> None:
    assert entity_provenance_key("c1", "section:a:1") == entity_provenance_key("c1", "section:a:1")
    assert entity_provenance_key("c1", "section:a:1") != entity_provenance_key("c2", "section:a:1")
    assert entity_provenance_key("c1", "section:a:1") != entity_provenance_key("c1", "section:a:2")


def test_provenance_keys_differ_by_relationship_type() -> None:
    contains = contains_provenance_key("doc-1", "chunk-1")
    supported = entity_provenance_key("chunk-1", "section:a:1")
    defines = source_fingerprint(
        "chunk-1", Relation("section:a:1", "concept:a:person", "DEFINES")
    )
    assert contains == contains_provenance_key("doc-1", "chunk-1")
    assert len({contains, supported, defines}) == 3


def test_duplicate_entity_mentions_are_deduplicated() -> None:
    text = "Section 1 applies. Section 1 applies again."
    entities = extract_entities(text, document_title="Act")
    sections = [e for e in entities if e.label == "Section"]
    assert len(sections) == 1


def test_defines_without_preceding_provision_is_skipped() -> None:
    text = 'defines "person" before any section.'
    entities = extract_entities(text, document_title="Act")
    relations = extract_relations(text, entities, document_title="Act")
    assert relations == []
