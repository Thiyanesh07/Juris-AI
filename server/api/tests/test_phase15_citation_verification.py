import pytest
from app.rag.citation_verifier import verify_citation_grounding, extract_legal_citations_from_text, VerifiedCitation


def test_extract_citations_regex():
    text = "In Maneka Gandhi v Union of India (1978) 1 SCC 248, also reported in AIR 1978 SC 597, the court held..."
    citations = extract_legal_citations_from_text(text)
    assert len(citations) >= 2
    assert any("1978" in c for c in citations)


def test_verify_citation_grounding_success():
    evidence_chunks = [
        {
            "rank": 1,
            "chunk_id": "chunk_001",
            "document_id": "doc_maneka_1978",
            "document_title": "Maneka Gandhi v. Union of India",
            "text": "Reported at (1978) 1 SCC 248. Right to personal liberty under Article 21.",
            "citation_ref": "(1978) 1 SCC 248",
            "page_start": 5,
            "page_end": 5,
        }
    ]
    
    verified = verify_citation_grounding(marker=1, evidence_rank=1, evidence_chunks=evidence_chunks)
    assert isinstance(verified, VerifiedCitation)
    assert verified.verification_status == "VERIFIED"
    assert verified.marker == 1
    assert verified.source_chunk_id == "chunk_001"
    assert verified.provenance_intact is True


def test_verify_citation_grounding_unverified_chunk():
    evidence_chunks = [
        {
            "rank": 1,
            "chunk_id": "chunk_001",
            "document_id": "doc_maneka_1978",
            "document_title": "Maneka Gandhi v. Union of India",
            "text": "Reported at (1978) 1 SCC 248.",
            "page_start": 5,
            "page_end": 5,
        }
    ]
    
    verified = verify_citation_grounding(marker=99, evidence_rank=99, evidence_chunks=evidence_chunks)
    assert isinstance(verified, VerifiedCitation)
    assert verified.verification_status == "UNVERIFIED"
    assert verified.confidence == 0.0
    assert verified.provenance_intact is False
