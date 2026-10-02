"""PDF validator — sanity-checks an uploaded file before expensive processing.

Checks performed (in order):
1. Magic bytes: file must start with ``%PDF``
2. PyMuPDF can open the document
3. Password protection: document must not be encrypted
4. Page count: at least 1 page
5. Image-only detection: at least one page must contain extractable text blocks
   (if every page is image-only the document is likely scanned and not supported)
"""

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz  # PyMuPDF (fitz alias)


@dataclass
class ValidationResult:
    """Structured outcome of PDF validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    page_count: int = 0
    is_scanned: bool = False

    @property
    def error_summary(self) -> str:
        return "; ".join(self.errors) if self.errors else ""


_PDF_MAGIC = b"%PDF"


def validate_pdf(path: Path) -> ValidationResult:
    """Validate *path* as an ingestion-ready PDF.

    Returns a :class:`ValidationResult`.  ``result.valid`` is ``True`` only
    when all checks pass.
    """
    errors: list[str] = []

    # ── 1. Magic bytes ──────────────────────────────────────────────────────
    try:
        with open(path, "rb") as fh:
            header = fh.read(1024)
    except OSError as exc:
        return ValidationResult(valid=False, errors=[f"Cannot read file: {exc}"])

    if _PDF_MAGIC not in header:
        return ValidationResult(valid=False, errors=["File is not a valid PDF (bad magic bytes)"])


    # ── 2. Open with PyMuPDF ────────────────────────────────────────────────
    try:
        doc = fitz.open(str(path))
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(valid=False, errors=[f"PyMuPDF cannot open file: {exc}"])

    try:
        # ── 3. Password protection ──────────────────────────────────────────
        if doc.is_encrypted:
            errors.append("PDF is password-protected and cannot be processed")
            return ValidationResult(valid=False, errors=errors)

        # ── 4. Page count ───────────────────────────────────────────────────
        page_count = len(doc)
        if page_count < 1:
            errors.append("PDF contains no pages")
            return ValidationResult(valid=False, errors=errors, page_count=0)

        # ── 5. Image-only / scanned detection ──────────────────────────────
        text_pages = 0
        # Sample up to the first 10 pages for speed on large documents.
        sample = min(page_count, 10)
        for i in range(sample):
            page = doc.load_page(i)
            blocks = page.get_text("blocks")  # type: ignore[arg-type]
            if any(b[6] == 0 for b in blocks):  # block_type 0 == text
                text_pages += 1

        is_scanned = text_pages == 0
        if is_scanned:
            errors.append(
                "PDF appears to be image-only / scanned. "
                "OCR is not supported; please upload a text-layer PDF."
            )
            return ValidationResult(
                valid=False,
                errors=errors,
                page_count=page_count,
                is_scanned=True,
            )

    finally:
        doc.close()

    return ValidationResult(valid=True, page_count=page_count)
