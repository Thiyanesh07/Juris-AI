"""Text extractor — pulls structured page-level text from a PDF via PyMuPDF.

Each page yields a :class:`PageRecord` with:
- ``page_number``: 1-indexed page number
- ``text``: concatenated text from all text blocks on that page
- ``blocks``: raw block list from ``page.get_text("blocks")`` for downstream use

Only text blocks (block_type == 0) are included; image blocks are ignored.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf as fitz  # PyMuPDF (fitz alias)


@dataclass
class PageRecord:
    """Extracted text and metadata for a single PDF page."""

    page_number: int  # 1-indexed
    text: str
    blocks: list[dict[str, Any]] = field(default_factory=list)


def extract_pages(pdf_path: Path) -> list[PageRecord]:
    """Open *pdf_path* with PyMuPDF and return one :class:`PageRecord` per page.

    Text blocks are sorted top-to-bottom then left-to-right (by their bounding
    box y0 coordinate, then x0) to approximate reading order.

    Only pages with at least one text block are returned; fully blank or
    image-only pages produce an empty-text ``PageRecord`` rather than being
    skipped so that page-number alignment is preserved.
    """
    doc = fitz.open(str(pdf_path))
    records: list[PageRecord] = []
    try:
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            raw_blocks = page.get_text("blocks")  # type: ignore[arg-type]

            # Sort by vertical position then horizontal position for reading order
            sorted_blocks = sorted(raw_blocks, key=lambda b: (b[1], b[0]))  # (y0, x0)

            # Filter to text blocks only (block_type 0)
            text_parts: list[str] = []
            block_dicts: list[dict[str, Any]] = []
            for b in sorted_blocks:
                if b[6] == 0:  # block_type: 0=text, 1=image
                    text_parts.append(b[4])
                    block_dicts.append(
                        {
                            "x0": b[0],
                            "y0": b[1],
                            "x1": b[2],
                            "y1": b[3],
                            "text": b[4],
                            "block_no": b[5],
                            "block_type": b[6],
                        }
                    )

            records.append(
                PageRecord(
                    page_number=page_index + 1,
                    text="\n".join(text_parts),
                    blocks=block_dicts,
                )
            )
    finally:
        doc.close()

    return records
