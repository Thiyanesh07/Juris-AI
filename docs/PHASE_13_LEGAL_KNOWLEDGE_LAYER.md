# Juris AI — Phase 13 Real Legal Knowledge Layer Documentation

> **Status**: Completed Phase 13  
> **Corpus**: 35-Document Legal Corpus (Constitution of India, 10 Major Acts, 4 Constitutional Amendments, 19 Supreme Court Judgments)

---

## 1. System Overview

Phase 13 establishes the real legal knowledge and data foundation for Juris AI, transforming raw PDF source documents into a traceable, structured legal representation:

```
Raw PDFs (data/legal_corpus_v1/raw/)
  └── Extracted Page-Level Text (processed/documents/)
       └── Legal-Aware Chunks & Structure (processed/chunks/)
            ├── InLegalBERT Embeddings & FAISS Vector Index (indexes/faiss/)
            ├── Legal Entities & Aliases Normalized (processed/entities/)
            └── Legal Relationships & Evidence Provenance (processed/relationships/)
                 └── Neo4j Knowledge Graph (indexes/neo4j/)
```

---

## 2. Directory & Artifact Layout

All generated outputs are separated from raw source data under `data/legal_corpus_v1/`:

```
data/legal_corpus_v1/
├── raw/                             ← Immutable source PDFs
│   ├── constitution/                (1 PDF: englishconstitution.pdf)
│   ├── acts/                        (10 PDFs: CrPC, IPC, IEA, BNS, BNSS, BSA, IT Act, RTI, etc.)
│   ├── constitutional_amendments/   (4 PDFs: 42nd, 44th, 73rd, 101st Amendments)
│   └── judgements/supreme_court/    (19 PDFs: Kesavananda Bharati, Maneka Gandhi, Shreya Singhal, etc.)
│
├── processed/                       ← Extracted JSON representations
│   ├── documents/                   (Page-level structured text per document)
│   ├── chunks/                      (Legal-aware chunks per document & all_chunks.json)
│   ├── entities/                    (Extracted legal entities & aliases per document)
│   └── relationships/               (Extracted legal relations with evidence & provenance)
│
├── metadata/                        ← Document registry & provenance tracking
│   ├── documents.json               (Document registry metadata & canonical identifiers)
│   ├── provenance.json              (Traceability back to raw PDFs and SHA-256 hashes)
│   └── versions.json               (Document versioning & temporal metadata foundation)
│
├── indexes/                         ← Search & graph indexes
│   ├── faiss/                       (index.faiss, embeddings.npy, metadata.json)
│   └── neo4j/                       (Neo4j schema constraints & database statistics)
│
├── checksums/
│   └── sha256.json                  (SHA-256 hashes for all raw PDFs)
│
└── evaluation/
    ├── questions.json               (Evaluation questions set)
    ├── expected_sources.json        (Ground-truth source documents)
    └── expected_citations.json      (Ground-truth legal citations)
```

---

## 3. Document Registry & Provenance Model

Every source document receives a stable internal `document_id` string (e.g., `constitution_of_india`, `crpc_1973`, `it_act_2000`, `kesavananda_bharati_1973`, `shreya_singhal_2015`).

### Document Schema (`metadata/documents.json`)

```json
{
  "document_id": "shreya_singhal_2015",
  "uuid": "4c13a447-06ff-5a82-bb34-1c6fa52140bb",
  "title": "Shreya Singhal v. Union of India",
  "document_type": "judgment",
  "legal_category": "Online Speech & Section 66A IT Act",
  "source_file": "judgements/supreme_court/11_shreya_singhal_2015.pdf",
  "issuing_authority": "Supreme Court of India",
  "jurisdiction": "India",
  "year": 2015,
  "citation": "(2015) 5 SCC 1",
  "language": "en",
  "checksum": "a82f...",
  "status": "ready"
}
```

---

## 4. Extraction & Legal Chunking Layer

### Text Extraction (`app/ingestion/extractor.py`)
- Extracted using PyMuPDF (`fitz`), preserving 1-based page numbers and text blocks.

### Legal-Aware Chunking (`app/ingestion/chunker.py`)
- Splits along structural boundaries (`PART`, `CHAPTER`, `SCHEDULE`, `ARTICLE`, `SECTION`).
- Configuration: ~2000 target characters, 4000 max characters, 200 overlap characters.
- Preserves `page_start`, `page_end`, and `hierarchy` JSON metadata.

---

## 5. Embeddings & FAISS Vector Index

- **Embedding Model**: `law-ai/InLegalBERT`
- **Pooling**: Attention-mask-aware mean pooling over final hidden states with L2-normalization.
- **Index Type**: `faiss.IndexFlatIP` (Cosine similarity over L2-normalized vectors).
- **On-Disk Persistence**: `index.faiss`, `embeddings.npy`, `metadata.json`.
- **Mapping Consistency**: `FAISS Vector Row -> Chunk ID -> Document ID -> Page/Section`.

---

## 6. Entity & Relationship Extraction Layer (`app/graph/extraction.py`)

### Legal Entity Types & Normalization
- `Article` (e.g., `article:constitution_of_india:21` $\rightarrow$ Article 21)
- `Section` (e.g., `section:it_act_2000:66a` $\rightarrow$ Section 66A)
- `Act` (e.g., `act:information-technology-act-2000` $\rightarrow$ Information Technology Act, 2000)
- `Amendment` (e.g., `amendment:const_amendment_44` $\rightarrow$ 44th Constitutional Amendment)
- `Judgment` (e.g., `judgment:kesavananda_bharati_1973` $\rightarrow$ Kesavananda Bharati)
- `Court` (e.g., `court:supreme-court-of-india` $\rightarrow$ Supreme Court of India)
- `Doctrine` (e.g., `doctrine:basic-structure-doctrine` $\rightarrow$ Basic Structure Doctrine)
- `Person` (e.g., `person:chandrachud-j` $\rightarrow$ Chandrachud J.)
- `Concept` (e.g., `concept:it_act_2000:computer-resource` $\rightarrow$ Computer Resource)

### Canonical Legal Relationships
- `DEFINES`: Section/Article defines Concept.
- `INTERPRETS`: Judgment interprets Article or Section.
- `AMENDS`: Amendment amends Article or Act.
- `REFERENCES` / `CITES`: Judgment references Act, Section, or Judgment.
- `OVERRULES`: Judgment overrules prior Judgment.
- `BELONGS_TO`: Article belongs to Constitution.

---

## 7. Neo4j Knowledge Graph Integration (`app/graph/client.py`)

### Node Labels
`Article`, `Act`, `Section`, `Amendment`, `Judgment`, `Court`, `Rule`, `Regulation`, `Concept`, `Person`, `Organization`, `Document`, `Chunk`, `Doctrine`.

### Constraints
Unique ID constraints enforced on all labels:
```cypher
CREATE CONSTRAINT FOR (n:Label) REQUIRE n.id IS UNIQUE
```

### Provenance Tracking
Every relationship in Neo4j includes:
`provenance_key`, `document_id`, `chunk_id`, `page`, `evidence_text`, `confidence`, `extraction_method`.

---

## 8. CLI Commands & Usage

Run full corpus ingestion:
```bash
uv run python -m app.cli ingest-corpus
```

Rebuild FAISS dense index:
```bash
uv run python -m app.cli rebuild-index
```

Populate Neo4j knowledge graph:
```bash
uv run python -m app.cli populate-graph
```

Run test suite:
```bash
uv run pytest
```
