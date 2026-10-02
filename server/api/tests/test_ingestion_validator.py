"""Unit tests for app/ingestion/validator.py."""

from pathlib import Path

from app.ingestion.validator import validate_pdf
from tests.helpers import make_image_only_pdf, make_minimal_legal_pdf, make_truncated_pdf


def _write_tmp(tmp_path: Path, data: bytes, name: str = "test.pdf") -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_valid_pdf_passes(tmp_path: Path) -> None:
    pdf_bytes = make_minimal_legal_pdf()
    path = _write_tmp(tmp_path, pdf_bytes)
    result = validate_pdf(path)
    assert result.valid is True
    assert result.page_count >= 1
    assert result.errors == []
    assert result.is_scanned is False


def test_not_a_pdf_fails_magic_bytes(tmp_path: Path) -> None:
    path = _write_tmp(tmp_path, b"Not a PDF at all", "notpdf.pdf")
    result = validate_pdf(path)
    assert result.valid is False
    assert any("magic" in e.lower() or "pdf" in e.lower() for e in result.errors)


def test_truncated_pdf_fails(tmp_path: Path) -> None:
    path = _write_tmp(tmp_path, make_truncated_pdf())
    result = validate_pdf(path)
    # May fail at magic bytes (passes) or at PyMuPDF open (passes)
    assert result.valid is False


def test_image_only_pdf_fails_scanned_check(tmp_path: Path) -> None:
    pdf_bytes = make_image_only_pdf()
    path = _write_tmp(tmp_path, pdf_bytes)
    result = validate_pdf(path)
    # Image-only PDFs should fail (either as scanned or page-count 0)
    # The key assertion: it's not considered valid for ingestion
    assert result.valid is False


def test_empty_file_fails(tmp_path: Path) -> None:
    path = _write_tmp(tmp_path, b"")
    result = validate_pdf(path)
    assert result.valid is False


def test_validation_result_error_summary(tmp_path: Path) -> None:
    path = _write_tmp(tmp_path, b"NOTPDF")
    result = validate_pdf(path)
    assert result.valid is False
    assert isinstance(result.error_summary, str)
    assert len(result.error_summary) > 0
