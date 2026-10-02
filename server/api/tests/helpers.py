"""Shared helpers for G03 tests — generates a minimal synthetic legal PDF."""

from __future__ import annotations

import io

import pymupdf as fitz  # PyMuPDF (fitz alias)

_LEGAL_TEXT = """\
PART I

THE UNION AND ITS TERRITORY

CHAPTER I

NAME AND TERRITORY OF THE UNION

Article 1

Name and territory of the Union.—

(1) India, that is Bharat, shall be a Union of States.

(2) The States and the territories thereof shall be as specified in the First Schedule.

(3) The territory of India shall comprise—

(a) the territories of the States;

(b) the Union territories specified in the First Schedule; and

(c) such other territories as may be acquired.

Article 2

Admission or establishment of new States.—Parliament may by law admit into the
Union, or establish, new States on such terms and conditions as it thinks fit.

PART II

CITIZENSHIP

Article 5

Citizenship at the commencement of the Constitution.—At the commencement of this
Constitution, every person who has his domicile in the territory of India and—

(a) who was born in the territory of India; or

(b) either of whose parents was born in the territory of India; or

(c) who has been ordinarily resident in the territory of India for not less than
five years immediately preceding such commencement,

shall be a citizen of India.

Provided that nothing in this article shall derogate from the provisions of any
law made or to be made by Parliament.

Explanation.— For the purposes of this article, the expression "Union Territory"
has the same meaning as in clause (30) of article 366.
"""


def make_minimal_legal_pdf() -> bytes:
    """Return the bytes of a minimal, text-layer legal PDF created with PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_text(
        (50, 50),
        _LEGAL_TEXT,
        fontsize=10,
        fontname="helv",
    )
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def make_image_only_pdf() -> bytes:
    """Return a PDF that contains only an image (no text layer) — should fail validation."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Draw a rectangle instead of text so there are no text blocks
    page.draw_rect(fitz.Rect(50, 50, 545, 792), color=(0, 0, 0))
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def make_truncated_pdf() -> bytes:
    """Return deliberately truncated bytes that look like a PDF but are corrupt."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>"
