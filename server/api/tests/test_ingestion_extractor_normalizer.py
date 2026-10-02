"""Unit tests for app/ingestion/extractor.py and app/ingestion/normalizer.py."""

from pathlib import Path

from app.ingestion.extractor import PageRecord, extract_pages
from app.ingestion.normalizer import normalize_text
from tests.helpers import make_minimal_legal_pdf


def _write_pdf(tmp_path: Path, data: bytes) -> Path:
    p = tmp_path / "test.pdf"
    p.write_bytes(data)
    return p


# ── Extractor tests ────────────────────────────────────────────────────────────


def test_extract_pages_returns_page_records(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, make_minimal_legal_pdf())
    pages = extract_pages(path)
    assert isinstance(pages, list)
    assert len(pages) >= 1
    for page in pages:
        assert isinstance(page, PageRecord)
        assert page.page_number >= 1


def test_extract_pages_are_1_indexed(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, make_minimal_legal_pdf())
    pages = extract_pages(path)
    page_numbers = [p.page_number for p in pages]
    assert page_numbers[0] == 1
    assert page_numbers == sorted(page_numbers)


def test_extract_pages_contain_legal_text(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, make_minimal_legal_pdf())
    pages = extract_pages(path)
    full_text = " ".join(p.text for p in pages)
    # The synthetic PDF contains known keywords
    assert "PART" in full_text or "Article" in full_text


def test_extract_pages_blocks_are_sorted(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, make_minimal_legal_pdf())
    pages = extract_pages(path)
    for page in pages:
        y0_values = [b["y0"] for b in page.blocks]
        assert y0_values == sorted(y0_values), "Blocks should be sorted top-to-bottom"


# ── Normalizer tests ───────────────────────────────────────────────────────────


def test_normalize_text_cleans_crlf() -> None:
    raw = "line one\r\nline two\r\n"
    result = normalize_text(raw)
    assert "\r" not in result
    assert "line one" in result
    assert "line two" in result


def test_normalize_text_merges_hyphenated_breaks() -> None:
    raw = "constitu-\ntion of India"
    result = normalize_text(raw)
    assert "constitution" in result.lower()


def test_normalize_text_preserves_article_identifiers() -> None:
    raw = "Article 15(2)(a) guarantees equality"
    result = normalize_text(raw)
    assert "Article 15(2)(a)" in result


def test_normalize_text_preserves_section_subsection() -> None:
    raw = "Section 3(1)(b) of the Act provides that"
    result = normalize_text(raw)
    assert "Section 3(1)(b)" in result


def test_normalize_text_collapses_blank_lines() -> None:
    raw = "line one\n\n\n\n\nline two"
    result = normalize_text(raw)
    assert "\n\n\n" not in result


def test_normalize_text_collapses_inline_spaces() -> None:
    raw = "word     another"
    result = normalize_text(raw)
    assert "word another" in result


def test_normalize_empty_string() -> None:
    assert normalize_text("") == ""


def test_normalize_preserves_proviso() -> None:
    raw = "Provided that nothing in this article shall apply"
    result = normalize_text(raw)
    assert "Provided that" in result
