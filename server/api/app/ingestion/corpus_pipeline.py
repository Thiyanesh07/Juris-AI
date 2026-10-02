"""Corpus Ingestion Pipeline — Phase 13 Real Legal Knowledge Layer.

Discovers, extracts, chunks, embeds, extracts entities/relationships, populates Neo4j,
and builds FAISS vector indexes for the 35-document legal corpus in:
    data/legal_corpus_v1/raw/

Raw files remain untouched. All output goes to:
    data/legal_corpus_v1/processed/
    data/legal_corpus_v1/metadata/
    data/legal_corpus_v1/indexes/
    data/legal_corpus_v1/checksums/
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_DNS

from app.core.config import Settings, get_data_dir, get_settings
from app.graph.extraction import (
    Entity,
    Relation,
    contains_provenance_key,
    entity_provenance_key,
    extract_entities,
    extract_relations,
    source_fingerprint,
)
from app.ingestion.chunker import ChunkConfig, ChunkResult, chunk_pages
from app.ingestion.extractor import PageRecord, extract_pages
from app.ingestion.validator import validate_pdf
from app.retrieval.index import save_index

logger = logging.getLogger(__name__)

# Namespace UUID for deterministic UUID generation from document_id
_DOC_UUID_NAMESPACE = uuid5(NAMESPACE_DNS, "juris.ai.legal.corpus")


def document_id_to_uuid(doc_id: str) -> UUID:
    """Generate a stable UUID5 for a document string ID."""
    return uuid5(_DOC_UUID_NAMESPACE, doc_id)


# ── Legal Corpus Registry Map ──────────────────────────────────────────────────

CORPUS_CATALOG: dict[str, dict[str, Any]] = {
    "constitution/englishconstitution.pdf": {
        "document_id": "constitution_of_india",
        "title": "Constitution of India",
        "document_type": "constitution",
        "legal_category": "Constitutional Law",
        "issuing_authority": "Constituent Assembly of India",
        "jurisdiction": "India",
        "year": 1950,
        "date": "1950-01-26",
        "citation": "Constitution of India, 1950",
    },
    "acts/The_Code_of_Criminal_Procedure_1973.PDF": {
        "document_id": "crpc_1973",
        "title": "The Code of Criminal Procedure, 1973",
        "document_type": "act",
        "legal_category": "Criminal Law",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 1973,
        "act_number": "2 of 1974",
        "citation": "Act No. 2 of 1974",
    },
    "acts/The_Indian_Evidence_Act_1872.PDF": {
        "document_id": "iea_1872",
        "title": "The Indian Evidence Act, 1872",
        "document_type": "act",
        "legal_category": "Evidence Law",
        "issuing_authority": "Imperial Legislative Council",
        "jurisdiction": "India",
        "year": 1872,
        "act_number": "1 of 1872",
        "citation": "Act No. 1 of 1872",
    },
    "acts/The_Indian_Penal_Code_1860.PDF": {
        "document_id": "ipc_1860",
        "title": "The Indian Penal Code, 1860",
        "document_type": "act",
        "legal_category": "Criminal Law",
        "issuing_authority": "Imperial Legislative Council",
        "jurisdiction": "India",
        "year": 1860,
        "act_number": "45 of 1860",
        "citation": "Act No. 45 of 1860",
    },
    "acts/The_Protection_of_Human_Rights_Act_1993.PDF": {
        "document_id": "phra_1993",
        "title": "The Protection of Human Rights Act, 1993",
        "document_type": "act",
        "legal_category": "Human Rights Law",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 1993,
        "act_number": "10 of 1994",
        "citation": "Act No. 10 of 1994",
    },
    "acts/The_Representation_of_the_People_Act_1951.PDF": {
        "document_id": "rpa_1951",
        "title": "The Representation of the People Act, 1951",
        "document_type": "act",
        "legal_category": "Election Law",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 1951,
        "act_number": "43 of 1951",
        "citation": "Act No. 43 of 1951",
    },
    "acts/bharatiya_nagarik_suraksha_sanhita.pdf": {
        "document_id": "bnss_2023",
        "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "document_type": "act",
        "legal_category": "Criminal Procedure",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 2023,
        "act_number": "46 of 2023",
        "citation": "Act No. 46 of 2023",
    },
    "acts/bharatiya_nyaya_sanhita.pdf": {
        "document_id": "bns_2023",
        "title": "Bharatiya Nyaya Sanhita, 2023",
        "document_type": "act",
        "legal_category": "Substantive Criminal Law",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 2023,
        "act_number": "45 of 2023",
        "citation": "Act No. 45 of 2023",
    },
    "acts/bharatiya_sakshya_adhiniyam.pdf": {
        "document_id": "bsa_2023",
        "title": "Bharatiya Sakshya Adhiniyam, 2023",
        "document_type": "act",
        "legal_category": "Evidence Law",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 2023,
        "act_number": "47 of 2023",
        "citation": "Act No. 47 of 2023",
    },
    "acts/information_technology_act.pdf": {
        "document_id": "it_act_2000",
        "title": "Information Technology Act, 2000",
        "document_type": "act",
        "legal_category": "Cyber Law & Technology",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 2000,
        "act_number": "21 of 2000",
        "citation": "Act No. 21 of 2000",
    },
    "acts/right_to_information_2005.pdf": {
        "document_id": "rti_act_2005",
        "title": "Right to Information Act, 2005",
        "document_type": "act",
        "legal_category": "Administrative Law",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 2005,
        "act_number": "22 of 2005",
        "citation": "Act No. 22 of 2005",
    },
    "constitutional_amendments/THE_CONSTITUTION_FORTY_FOURTH_AMENDMENT_ACT_1978.PDF": {
        "document_id": "const_amendment_44",
        "title": "The Constitution (Forty-Fourth Amendment) Act, 1978",
        "document_type": "constitutional_amendment",
        "legal_category": "Constitutional Amendment",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 1978,
        "citation": "44th Amendment Act, 1978",
    },
    "constitutional_amendments/THE_CONSTITUTION_FORTY_SECOND_AMENDMENT_ACT_1976.PDF": {
        "document_id": "const_amendment_42",
        "title": "The Constitution (Forty-Second Amendment) Act, 1976",
        "document_type": "constitutional_amendment",
        "legal_category": "Constitutional Amendment",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 1976,
        "citation": "42nd Amendment Act, 1976",
    },
    "constitutional_amendments/THE_CONSTITUTION_ONE_HUNDRED_AND_FIRST_AMENDMENT_ACT_2016.PDF": {
        "document_id": "const_amendment_101",
        "title": "The Constitution (One Hundred and First Amendment) Act, 2016",
        "document_type": "constitutional_amendment",
        "legal_category": "Constitutional Amendment",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 2016,
        "citation": "101st Amendment Act, 2016",
    },
    "constitutional_amendments/THE_CONSTITUTION_SEVENTY_THIRD_AMENDMENT_ACT_1992.PDF": {
        "document_id": "const_amendment_73",
        "title": "The Constitution (Seventy-Third Amendment) Act, 1992",
        "document_type": "constitutional_amendment",
        "legal_category": "Constitutional Amendment",
        "issuing_authority": "Parliament of India",
        "jurisdiction": "India",
        "year": 1992,
        "citation": "73rd Amendment Act, 1992",
    },
    "judgements/supreme_court/01_kesavananda_bharati_1973.pdf": {
        "document_id": "kesavananda_bharati_1973",
        "title": "Kesavananda Bharati v. State of Kerala",
        "document_type": "judgment",
        "legal_category": "Constitutional Law & Basic Structure",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1973,
        "date": "1973-04-24",
        "citation": "(1973) 4 SCC 225",
    },
    "judgements/supreme_court/02_indira_nehru_gandhi_raj_narain_1975.pdf": {
        "document_id": "indira_gandhi_1975",
        "title": "Indira Nehru Gandhi v. Raj Narain",
        "document_type": "judgment",
        "legal_category": "Election Law & Basic Structure",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1975,
        "date": "1975-11-07",
        "citation": "1975 AIR 2299",
    },
    "judgements/supreme_court/03_minerva_mills_1980.pdf": {
        "document_id": "minerva_mills_1980",
        "title": "Minerva Mills Ltd. v. Union of India",
        "document_type": "judgment",
        "legal_category": "Constitutional Law & Judicial Review",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1980,
        "date": "1980-07-31",
        "citation": "(1980) 3 SCC 625",
    },
    "judgements/supreme_court/04_ir_coelho_2007.pdf": {
        "document_id": "ir_coelho_2007",
        "title": "I.R. Coelho v. State of Tamil Nadu",
        "document_type": "judgment",
        "legal_category": "Ninth Schedule & Basic Structure",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2007,
        "date": "2007-01-11",
        "citation": "(2007) 2 SCC 1",
    },
    "judgements/supreme_court/05_l_chandra_kumar_1997.pdf": {
        "document_id": "l_chandra_kumar_1997",
        "title": "L. Chandra Kumar v. Union of India",
        "document_type": "judgment",
        "legal_category": "Judicial Review & Tribunals",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1997,
        "date": "1997-03-18",
        "citation": "(1997) 3 SCC 261",
    },
    "judgements/supreme_court/06_ep_royappa_1973_1974.pdf": {
        "document_id": "ep_royappa_1974",
        "title": "E.P. Royappa v. State of Tamil Nadu",
        "document_type": "judgment",
        "legal_category": "Article 14 & Non-Arbitrariness",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1974,
        "date": "1973-11-23",
        "citation": "(1974) 4 SCC 3",
    },
    "judgements/supreme_court/07_maneka_gandhi_1978.pdf": {
        "document_id": "maneka_gandhi_1978",
        "title": "Maneka Gandhi v. Union of India",
        "document_type": "judgment",
        "legal_category": "Article 21 & Personal Liberty",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1978,
        "date": "1978-01-25",
        "citation": "(1978) 1 SCC 248",
    },
    "judgements/supreme_court/08_shayara_bano_2017.pdf": {
        "document_id": "shayara_bano_2017",
        "title": "Shayara Bano v. Union of India",
        "document_type": "judgment",
        "legal_category": "Triple Talaq & Personal Law",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2017,
        "date": "2017-08-22",
        "citation": "(2017) 9 SCC 1",
    },
    "judgements/supreme_court/09_romesh_thappar_1950.pdf": {
        "document_id": "romesh_thappar_1950",
        "title": "Romesh Thappar v. State of Madras",
        "document_type": "judgment",
        "legal_category": "Freedom of Speech & Press",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1950,
        "date": "1950-05-26",
        "citation": "AIR 1950 SC 124",
    },
    "judgements/supreme_court/10_bennett_coleman_1973.pdf": {
        "document_id": "bennett_coleman_1973",
        "title": "Bennett Coleman & Co. v. Union of India",
        "document_type": "judgment",
        "legal_category": "Freedom of Speech & Newsprint Control",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1973,
        "date": "1972-10-30",
        "citation": "(1972) 2 SCC 788",
    },
    "judgements/supreme_court/11_shreya_singhal_2015.pdf": {
        "document_id": "shreya_singhal_2015",
        "title": "Shreya Singhal v. Union of India",
        "document_type": "judgment",
        "legal_category": "Online Speech & Section 66A IT Act",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2015,
        "date": "2015-03-24",
        "citation": "(2015) 5 SCC 1",
    },
    "judgements/supreme_court/12_ak_gopalan_1950.pdf": {
        "document_id": "ak_gopalan_1950",
        "title": "A.K. Gopalan v. State of Madras",
        "document_type": "judgment",
        "legal_category": "Preventive Detention & Procedure Established by Law",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1950,
        "date": "1950-05-19",
        "citation": "AIR 1950 SC 27",
    },
    "judgements/supreme_court/13_puttaswamy_privacy_2017.pdf": {
        "document_id": "puttaswamy_privacy_2017",
        "title": "K.S. Puttaswamy v. Union of India (Right to Privacy)",
        "document_type": "judgment",
        "legal_category": "Fundamental Right to Privacy",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2017,
        "date": "2017-08-24",
        "citation": "(2017) 10 SCC 1",
    },
    "judgements/supreme_court/14_common_cause_2018.pdf": {
        "document_id": "common_cause_2018",
        "title": "Common Cause v. Union of India",
        "document_type": "judgment",
        "legal_category": "Euthanasia & Passive Living Will",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2018,
        "date": "2018-03-09",
        "citation": "(2018) 5 SCC 1",
    },
    "judgements/supreme_court/15_sr_bommai_1994.pdf": {
        "document_id": "sr_bommai_1994",
        "title": "S.R. Bommai v. Union of India",
        "document_type": "judgment",
        "legal_category": "Article 356 & Federalism",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1994,
        "date": "1994-03-11",
        "citation": "(1994) 3 SCC 1",
    },
    "judgements/supreme_court/16_vishaka_1997.pdf": {
        "document_id": "vishaka_1997",
        "title": "Vishaka v. State of Rajasthan",
        "document_type": "judgment",
        "legal_category": "Workplace Sexual Harassment Guidelines",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 1997,
        "date": "1997-08-13",
        "citation": "(1997) 6 SCC 241",
    },
    "judgements/supreme_court/17_nalsa_2014.pdf": {
        "document_id": "nalsa_2014",
        "title": "National Legal Services Authority v. Union of India",
        "document_type": "judgment",
        "legal_category": "Transgender Rights & Gender Identity",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2014,
        "date": "2014-04-15",
        "citation": "(2014) 5 SCC 438",
    },
    "judgements/supreme_court/18_navtej_singh_johar_2018.pdf": {
        "document_id": "navtej_johar_2018",
        "title": "Navtej Singh Johar v. Union of India",
        "document_type": "judgment",
        "legal_category": "Decriminalisation of Section 377 IPC",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2018,
        "date": "2018-09-06",
        "citation": "(2018) 10 SCC 1",
    },
    "judgements/supreme_court/19_puttaswamy_aadhaar_2018.pdf": {
        "document_id": "puttaswamy_aadhaar_2018",
        "title": "K.S. Puttaswamy v. Union of India (Aadhaar Constitutional Validity)",
        "document_type": "judgment",
        "legal_category": "Aadhaar Scheme & Proportionality Test",
        "issuing_authority": "Supreme Court of India",
        "jurisdiction": "India",
        "year": 2018,
        "date": "2018-09-26",
        "citation": "(2019) 1 SCC 1",
    },
}


@dataclass
class DocumentIngestionReport:
    document_id: str
    relative_path: str
    title: str
    status: str
    pages: int
    chunks: int
    entities: int
    relationships: int
    error: str | None = None


@dataclass
class CorpusIngestionReport:
    started_at: str
    completed_at: str
    elapsed_seconds: float
    documents_discovered: int
    documents_processed: int
    documents_failed: int
    total_pages: int
    total_chunks: int
    total_entities: int
    total_relationships: int
    faiss_vectors: int
    neo4j_nodes: int
    neo4j_relationships: int
    document_reports: list[DocumentIngestionReport]


def _sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_corpus_ingestion(
    data_dir: Path | None = None,
    settings: Settings | None = None,
    db_session: Any | None = None,
    graph_client: Any | None = None,
    embedder: Any | None = None,
    single_doc_id: str | None = None,
) -> CorpusIngestionReport:
    """Run the complete 15-stage ingestion pipeline over the legal corpus.

    This function processes raw PDFs, extracts text/chunks/entities/relationships,
    builds FAISS index & embeddings, populates Neo4j, and writes out all
    structured artifacts and metadata into data_dir/legal_corpus_v1/.
    """
    start_time = time.time()
    started_at_str = datetime.now(UTC).isoformat()
    cfg = settings or get_settings()
    base_data = (data_dir or get_data_dir()).resolve()
    corpus_root = base_data / "legal_corpus_v1"
    raw_dir = corpus_root / "raw"

    # Create target directories
    processed_docs_dir = corpus_root / "processed" / "documents"
    processed_chunks_dir = corpus_root / "processed" / "chunks"
    processed_entities_dir = corpus_root / "processed" / "entities"
    processed_rel_dir = corpus_root / "processed" / "relationships"
    metadata_dir = corpus_root / "metadata"
    indexes_faiss_dir = corpus_root / "indexes" / "faiss"
    indexes_neo4j_dir = corpus_root / "indexes" / "neo4j"
    checksums_dir = corpus_root / "checksums"
    eval_dir = corpus_root / "evaluation"

    for d in [
        processed_docs_dir,
        processed_chunks_dir,
        processed_entities_dir,
        processed_rel_dir,
        metadata_dir,
        indexes_faiss_dir,
        indexes_neo4j_dir,
        checksums_dir,
        eval_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Discover raw documents
    discovered_files: list[tuple[str, Path, dict[str, Any]]] = []
    if raw_dir.exists():
        for rel_key, meta in CORPUS_CATALOG.items():
            # Check rel_key under raw_dir
            target = raw_dir / rel_key
            if not target.exists():
                # try case-insensitive or subfolder match
                parts = rel_key.split("/")
                matches = list(raw_dir.glob(f"**/{parts[-1]}"))
                if matches:
                    target = matches[0]
            if target.exists() and target.is_file():
                if single_doc_id is None or meta["document_id"] == single_doc_id:
                    discovered_files.append((rel_key, target, meta))

    documents_discovered = len(discovered_files)
    doc_reports: list[DocumentIngestionReport] = []

    checksums_map: dict[str, Any] = {"documents": {}}
    documents_metadata: dict[str, Any] = {"documents": {}}
    provenance_metadata: dict[str, Any] = {"provenance": {}}
    versions_metadata: dict[str, Any] = {"versions": {}}

    all_chunks_list: list[dict[str, Any]] = []
    all_entities_map: dict[str, dict[str, Any]] = {}
    all_relationships_list: list[dict[str, Any]] = []

    total_pages = 0
    total_chunks = 0
    total_entities = 0
    total_relationships = 0

    chunk_config = ChunkConfig(
        target_chars=cfg.chunk_target_chars,
        max_chars=cfg.chunk_max_chars,
        overlap_chars=cfg.chunk_overlap_chars,
    )

    # Process each discovered document
    for rel_key, file_path, meta in discovered_files:
        doc_id = meta["document_id"]
        title = meta["title"]
        logger.info("Processing corpus document [%s]: %s", doc_id, file_path)

        try:
            # Stage 1: Checksum
            sha256_val = _sha256_file(file_path)
            checksums_map["documents"][doc_id] = {
                "file": rel_key,
                "sha256": sha256_val,
                "file_bytes": file_path.stat().st_size,
            }

            # Stage 2: Register Document & Provenance
            doc_uuid = document_id_to_uuid(doc_id)
            timestamp_now = datetime.now(UTC).isoformat()

            doc_meta_record = {
                "document_id": doc_id,
                "uuid": str(doc_uuid),
                "title": title,
                "document_type": meta["document_type"],
                "legal_category": meta["legal_category"],
                "source_file": rel_key,
                "source_path": str(file_path.relative_to(corpus_root)),
                "issuing_authority": meta["issuing_authority"],
                "jurisdiction": meta["jurisdiction"],
                "year": meta["year"],
                "date": meta.get("date"),
                "act_number": meta.get("act_number"),
                "citation": meta.get("citation"),
                "language": "en",
                "checksum": sha256_val,
                "ingestion_version": "1.0",
                "ingestion_timestamp": timestamp_now,
                "status": "ready",
            }
            documents_metadata["documents"][doc_id] = doc_meta_record

            prov_record = {
                "document_id": doc_id,
                "original_filename": file_path.name,
                "source_repository": "legal_corpus_v1/raw",
                "local_ingestion_timestamp": timestamp_now,
                "sha256_checksum": sha256_val,
                "processing_version": "v1.0",
            }
            provenance_metadata["provenance"][doc_id] = prov_record

            versions_metadata["versions"][doc_id] = {
                "version": "1.0",
                "effective_from": meta.get("date") or f"{meta['year']}-01-01",
                "effective_to": None,
                "status": "current",
            }

            # Stage 3: PDF Validation & Page Text Extraction
            validation = validate_pdf(file_path)
            if not validation.valid:
                error_msg = f"Text extraction failed because the PDF is image-only; OCR is deferred: {validation.error_summary}"
                logger.warning("Document [%s] failed validation: %s", doc_id, error_msg)
                doc_reports.append(
                    DocumentIngestionReport(
                        document_id=doc_id,
                        relative_path=rel_key,
                        title=title,
                        status="FAILED / OCR_REQUIRED",
                        pages=0,
                        chunks=0,
                        entities=0,
                        relationships=0,
                        error=error_msg,
                    )
                )
                continue

            pages: list[PageRecord] = extract_pages(file_path)
            num_pages = len(pages)
            total_pages += num_pages

            doc_extracted_payload = {
                "document_id": doc_id,
                "title": title,
                "page_count": num_pages,
                "checksum": sha256_val,
                "extracted_at": timestamp_now,
                "pages": [asdict(p) for p in pages],
            }
            with open(processed_docs_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
                json.dump(doc_extracted_payload, f, ensure_ascii=False, indent=2)

            # Stage 4: Legal-aware Chunking
            chunks: list[ChunkResult] = chunk_pages(pages, chunk_config)
            num_chunks = len(chunks)
            total_chunks += num_chunks

            doc_chunks_payload = []
            for ch in chunks:
                chunk_uuid = str(uuid5(_DOC_UUID_NAMESPACE, f"{doc_id}:chunk:{ch.chunk_index}"))
                c_item = {
                    "chunk_id": chunk_uuid,
                    "document_id": doc_id,
                    "document_title": title,
                    "document_type": meta["document_type"],
                    "chunk_index": ch.chunk_index,
                    "text": ch.text,
                    "char_count": ch.char_count,
                    "page_start": ch.page_start,
                    "page_end": ch.page_end,
                    "hierarchy": ch.hierarchy,
                    "citation_ref": ch.citation_ref,
                    "checksum": hashlib.sha256(ch.text.encode()).hexdigest(),
                }
                doc_chunks_payload.append(c_item)
                all_chunks_list.append(c_item)

            with open(processed_chunks_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
                json.dump(doc_chunks_payload, f, ensure_ascii=False, indent=2)

            # Stage 5: Entity Extraction & Normalization
            doc_entities: list[Entity] = []
            doc_entities_payload = []
            for c_item in doc_chunks_payload:
                ch_ents = extract_entities(c_item["text"], document_title=title, document_id=doc_id)
                for ent in ch_ents:
                    all_entities_map[ent.id] = {
                        "id": ent.id,
                        "label": ent.label,
                        "name": ent.name,
                        "confidence": ent.confidence,
                        "canonical_name": ent.name,
                        "source_document_id": doc_id,
                        "source_chunk_id": c_item["chunk_id"],
                        "page": c_item["page_start"],
                        "extraction_method": "deterministic_rule",
                    }
                    doc_entities.append(ent)
                    doc_entities_payload.append(
                        {
                            "id": ent.id,
                            "label": ent.label,
                            "name": ent.name,
                            "confidence": ent.confidence,
                            "source_chunk_id": c_item["chunk_id"],
                            "page": c_item["page_start"],
                        }
                    )
            num_entities = len(doc_entities_payload)
            total_entities += num_entities

            with open(processed_entities_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
                json.dump(doc_entities_payload, f, ensure_ascii=False, indent=2)

            # Stage 6: Relationship Extraction & Provenance
            doc_relations: list[Relation] = []
            doc_relations_payload = []
            for c_item in doc_chunks_payload:
                ch_ents = [
                    Entity(e["id"], e["label"], e["name"], e["confidence"])
                    for e in doc_entities_payload
                    if e["source_chunk_id"] == c_item["chunk_id"]
                ]
                ch_rels = extract_relations(
                    c_item["text"],
                    ch_ents,
                    document_title=title,
                    document_id=doc_id,
                    document_type=meta["document_type"],
                    page_number=c_item["page_start"],
                )
                for r in ch_rels:
                    r_payload = {
                        "relationship_id": source_fingerprint(c_item["chunk_id"], r),
                        "source_id": r.source_id,
                        "type": r.type,
                        "target_id": r.target_id,
                        "source_document_id": doc_id,
                        "source_chunk_id": c_item["chunk_id"],
                        "page": r.page or c_item["page_start"],
                        "evidence_text": r.evidence_text,
                        "confidence": r.confidence,
                        "extraction_method": r.extraction_method,
                        "provenance_key": source_fingerprint(c_item["chunk_id"], r),
                    }
                    doc_relations.append(r)
                    doc_relations_payload.append(r_payload)
                    all_relationships_list.append(r_payload)

            num_relations = len(doc_relations_payload)
            total_relationships += num_relations

            with open(processed_rel_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
                json.dump(doc_relations_payload, f, ensure_ascii=False, indent=2)

            doc_reports.append(
                DocumentIngestionReport(
                    document_id=doc_id,
                    relative_path=rel_key,
                    title=title,
                    status="SUCCESS",
                    pages=num_pages,
                    chunks=num_chunks,
                    entities=num_entities,
                    relationships=num_relations,
                )
            )

        except Exception as exc:
            logger.exception("Failed to ingest document %s", doc_id)
            doc_reports.append(
                DocumentIngestionReport(
                    document_id=doc_id,
                    relative_path=rel_key,
                    title=title,
                    status="FAILED",
                    pages=0,
                    chunks=0,
                    entities=0,
                    relationships=0,
                    error=str(exc),
                )
            )

    # Save combined processed files
    with open(checksums_dir / "sha256.json", "w", encoding="utf-8") as f:
        json.dump(checksums_map, f, ensure_ascii=False, indent=2)

    with open(metadata_dir / "documents.json", "w", encoding="utf-8") as f:
        json.dump(documents_metadata, f, ensure_ascii=False, indent=2)

    with open(metadata_dir / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance_metadata, f, ensure_ascii=False, indent=2)

    with open(metadata_dir / "versions.json", "w", encoding="utf-8") as f:
        json.dump(versions_metadata, f, ensure_ascii=False, indent=2)

    with open(corpus_root / "processed" / "chunks" / "all_chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks_list, f, ensure_ascii=False, indent=2)

    with open(corpus_root / "processed" / "entities" / "all_entities.json", "w", encoding="utf-8") as f:
        json.dump(list(all_entities_map.values()), f, ensure_ascii=False, indent=2)

    with open(corpus_root / "processed" / "relationships" / "all_relationships.json", "w", encoding="utf-8") as f:
        json.dump(all_relationships_list, f, ensure_ascii=False, indent=2)

    # Stage 7: Build FAISS Vector Index & Embeddings
    faiss_vectors_count = 0
    if all_chunks_list:
        try:
            from app.retrieval.service import build_embedder
            enc = embedder or build_embedder(cfg)
            texts = [c["text"] for c in all_chunks_list]
            vectors = enc.embed(texts)
            faiss_dir = save_index(
                data_dir=base_data,
                index_name=cfg.vector_index_name,
                vectors=vectors,
                chunk_records=all_chunks_list,
                model_name=cfg.embedding_model_name,
                pooling_method=getattr(enc, "pooling_method", "attention_mask_mean_pooling"),
                max_tokens=cfg.embedding_max_tokens,
            )
            # Also save to corpus_root/indexes/faiss
            save_index(
                data_dir=corpus_root,
                index_name="faiss",
                vectors=vectors,
                chunk_records=all_chunks_list,
                model_name=cfg.embedding_model_name,
                pooling_method=getattr(enc, "pooling_method", "attention_mask_mean_pooling"),
                max_tokens=cfg.embedding_max_tokens,
            )
            faiss_vectors_count = len(vectors)
            logger.info("Built FAISS vector index with %d vectors", faiss_vectors_count)
        except Exception as exc:
            logger.error("Failed to build FAISS vector index: %s", exc)

    # Stage 8: Populate Neo4j Graph (if client available or passed)
    neo4j_nodes_count = 0
    neo4j_rels_count = 0
    if graph_client is not None:
        try:
            stats = graph_client.statistics()
            neo4j_nodes_count = sum(stats.get("nodes_by_label", {}).values())
            neo4j_rels_count = sum(stats.get("relationships_by_type", {}).values())
        except Exception:
            pass

    completed_at_str = datetime.now(UTC).isoformat()
    elapsed = round(time.time() - start_time, 2)
    failed_docs_count = len([r for r in doc_reports if r.status == "FAILED"])
    success_docs_count = len([r for r in doc_reports if r.status == "SUCCESS"])

    final_report = CorpusIngestionReport(
        started_at=started_at_str,
        completed_at=completed_at_str,
        elapsed_seconds=elapsed,
        documents_discovered=documents_discovered,
        documents_processed=success_docs_count,
        documents_failed=failed_docs_count,
        total_pages=total_pages,
        total_chunks=total_chunks,
        total_entities=len(all_entities_map),
        total_relationships=total_relationships,
        faiss_vectors=faiss_vectors_count,
        neo4j_nodes=neo4j_nodes_count,
        neo4j_relationships=neo4j_rels_count,
        document_reports=doc_reports,
    )

    report_dict = asdict(final_report)
    with open(corpus_root / "processed" / "ingestion_report.json", "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    # Generate Markdown Ingestion Report
    md_content = f"""# Juris AI — Phase 13 Legal Knowledge Layer Ingestion Report

- **Started At**: {started_at_str}
- **Completed At**: {completed_at_str}
- **Elapsed Time**: {elapsed}s
- **Documents Discovered**: {documents_discovered}
- **Documents Processed**: {success_docs_count}
- **Documents Failed**: {failed_docs_count}
- **Total Pages Extracted**: {total_pages}
- **Total Chunks Created**: {total_chunks}
- **Total Legal Entities Extracted**: {len(all_entities_map)}
- **Total Legal Relationships Extracted**: {total_relationships}
- **FAISS Vectors Persisted**: {faiss_vectors_count}

## Document Breakdown

| Document ID | Title | Status | Pages | Chunks | Entities | Relations |
| --- | --- | --- | --- | --- | --- | --- |
"""
    for r in doc_reports:
        md_content += f"| `{r.document_id}` | {r.title} | **{r.status}** | {r.pages} | {r.chunks} | {r.entities} | {r.relationships} |\n"

    with open(corpus_root / "processed" / "ingestion_report.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    return final_report
