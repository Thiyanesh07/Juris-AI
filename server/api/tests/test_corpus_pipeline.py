"""Automated tests for Phase 13.1 Real Legal Knowledge Layer Verification & Correction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.graph.extraction import (
    Entity,
    Relation,
    extract_entities,
    extract_relations,
)
from app.ingestion.corpus_pipeline import (
    CORPUS_CATALOG,
    _sha256_file,
    document_id_to_uuid,
    run_corpus_ingestion,
)


def test_corpus_catalog_discovery(tmp_path: Path) -> None:
    """Verify that catalog entries contain all required legal metadata fields."""
    assert len(CORPUS_CATALOG) >= 34
    for rel_path, meta in CORPUS_CATALOG.items():
        assert "document_id" in meta
        assert "title" in meta
        assert "document_type" in meta
        assert "legal_category" in meta
        assert "issuing_authority" in meta
        assert "jurisdiction" in meta
        assert "year" in meta


def test_document_id_to_uuid_is_deterministic() -> None:
    """Verify that document_id_to_uuid is stable and reproducible."""
    uuid1 = document_id_to_uuid("constitution_of_india")
    uuid2 = document_id_to_uuid("constitution_of_india")
    uuid3 = document_id_to_uuid("kesavananda_bharati_1973")
    assert uuid1 == uuid2
    assert uuid1 != uuid3


class DummyEmbedder:
    pooling_method = "attention_mask_mean_pooling"
    normalization = "l2"

    def embed(self, texts: list[str]) -> Any:
        import numpy as np

        mat = np.zeros((len(texts), 768), dtype=np.float32)
        mat[:, 0] = 1.0
        return mat


def test_constitution_node_typing() -> None:
    """Verify Constitution is typed as (:Constitution {id: 'constitution:india'}) and Articles use BELONGS_TO."""
    text = "Article 21 protects life and personal liberty under the Constitution of India."
    ents = extract_entities(text, document_title="Constitution of India", document_id="constitution_of_india")

    const_ent = next((e for e in ents if e.id == "constitution:india"), None)
    assert const_ent is not None
    assert const_ent.label == "Constitution"
    assert const_ent.name == "Constitution of India"

    art_ent = next((e for e in ents if e.id == "article:constitution_of_india:21"), None)
    assert art_ent is not None
    assert art_ent.label == "Article"

    rels = extract_relations(text, ents, document_title="Constitution of India", document_id="constitution_of_india", document_type="constitution")
    belongs_to_rel = next((r for r in rels if r.type == "BELONGS_TO" and r.source_id == "article:constitution_of_india:21"), None)
    assert belongs_to_rel is not None
    assert belongs_to_rel.target_id == "constitution:india"


def test_act_entity_blacklist_and_canonical_normalization() -> None:
    """Verify generic terms are blacklisted and canonical Acts normalize correctly."""
    text = "Under the Information Technology Act, 2000, Section 66A was struck down. The principal Act and Objects and Reasons of the Act were considered."
    ents = extract_entities(text, document_title="Shreya Singhal v. Union of India", document_id="shreya_singhal_2015")

    ent_ids = {e.id for e in ents}
    ent_names = {e.name.lower() for e in ents}

    assert "act:it_act_2000" in ent_ids
    assert "act:the-principal-act" not in ent_ids
    assert "act:objects-and-reasons" not in ent_ids
    assert "the act" not in ent_names
    assert "principal act" not in ent_names


def test_relationship_evidence_and_direction() -> None:
    """Verify semantic relations require explicit evidence text and correct direction."""
    text = "In Maneka Gandhi v. Union of India, the Supreme Court held that Article 21 includes the right to travel abroad."
    ents = extract_entities(text, document_title="Maneka Gandhi v. Union of India", document_id="maneka_gandhi_1978")

    rels = extract_relations(text, ents, document_title="Maneka Gandhi v. Union of India", document_id="maneka_gandhi_1978", document_type="judgment")

    interprets_rel = next((r for r in rels if r.type == "INTERPRETS" and r.target_id == "article:constitution_of_india:21"), None)
    assert interprets_rel is not None
    assert interprets_rel.source_id in ("judgment:maneka-gandhi-v-union-of-india", "judgment:maneka_gandhi_1978")
    assert "interprets" in interprets_rel.evidence_text.lower() or "maneka" in interprets_rel.evidence_text.lower()


def test_raw_pdf_immutability() -> None:
    """Verify that all raw PDF source files remain byte-for-byte unchanged."""
    data_dir = Path(__file__).resolve().parents[3] / "data" / "legal_corpus_v1"
    raw_dir = data_dir / "raw"
    checksum_file = data_dir / "checksums" / "sha256.json"

    if not checksum_file.exists():
        pytest.skip("Checksum file not generated yet")

    stored_checksums = json.loads(checksum_file.read_text(encoding="utf-8"))["documents"]

    for doc_id, meta in stored_checksums.items():
        rel_file = meta["file"]
        target_path = raw_dir / rel_file
        if not target_path.exists():
            parts = rel_file.split("/")
            matches = list(raw_dir.glob(f"**/{parts[-1]}"))
            if matches:
                target_path = matches[0]
        if target_path.exists():
            current_hash = _sha256_file(target_path)
            assert current_hash == meta["sha256"], f"Raw PDF {rel_file} was modified!"


def test_corpus_ingestion_pipeline_execution(tmp_path: Path) -> None:
    """Test full ingestion pipeline run on a single test document."""
    corpus_root = tmp_path / "legal_corpus_v1"
    raw_acts_dir = corpus_root / "raw" / "acts"
    raw_acts_dir.mkdir(parents=True, exist_ok=True)

    sample_pdf = Path(__file__).resolve().parents[3] / "data" / "legal_corpus_v1" / "raw" / "acts" / "right_to_information_2005.pdf"
    if not sample_pdf.exists():
        pytest.skip("Raw corpus files not present in workspace")

    dest_pdf = raw_acts_dir / "right_to_information_2005.pdf"
    dest_pdf.write_bytes(sample_pdf.read_bytes())

    report = run_corpus_ingestion(
        data_dir=tmp_path,
        single_doc_id="rti_act_2005",
        embedder=DummyEmbedder(),
    )

    assert report.documents_discovered >= 1
    assert report.documents_processed >= 1
    assert report.documents_failed == 0
    assert report.total_pages > 0
    assert report.total_chunks > 0
    assert report.total_entities > 0

    checksum_file = corpus_root / "checksums" / "sha256.json"
    assert checksum_file.exists()
    checksums = json.loads(checksum_file.read_text(encoding="utf-8"))
    assert "rti_act_2005" in checksums["documents"]
    assert len(checksums["documents"]["rti_act_2005"]["sha256"]) == 64

    metadata_file = corpus_root / "metadata" / "documents.json"
    assert metadata_file.exists()
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert "rti_act_2005" in metadata["documents"]
    assert metadata["documents"]["rti_act_2005"]["document_type"] == "act"


def test_idempotent_reingestion(tmp_path: Path) -> None:
    """Verify running ingestion twice produces identical chunk and entity metrics."""
    sample_pdf = Path(__file__).resolve().parents[3] / "data" / "legal_corpus_v1" / "raw" / "acts" / "right_to_information_2005.pdf"
    if not sample_pdf.exists():
        pytest.skip("Raw corpus files not present in workspace")

    corpus_root = tmp_path / "legal_corpus_v1"
    raw_acts_dir = corpus_root / "raw" / "acts"
    raw_acts_dir.mkdir(parents=True, exist_ok=True)
    dest_pdf = raw_acts_dir / "right_to_information_2005.pdf"
    dest_pdf.write_bytes(sample_pdf.read_bytes())

    report1 = run_corpus_ingestion(data_dir=tmp_path, single_doc_id="rti_act_2005", embedder=DummyEmbedder())
    report2 = run_corpus_ingestion(data_dir=tmp_path, single_doc_id="rti_act_2005", embedder=DummyEmbedder())

    assert report1.total_chunks == report2.total_chunks
    assert report1.total_entities == report2.total_entities
    assert report1.total_relationships == report2.total_relationships
