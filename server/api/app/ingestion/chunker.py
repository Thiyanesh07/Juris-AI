"""Hierarchy-aware legal document chunker.

Strategy
--------
1. Split the full document text into lines and run hierarchy detection.
2. Group consecutive lines into *provisions* — a provision boundary is crossed
   whenever a PART, CHAPTER, SCHEDULE, ARTICLE, or SECTION header is seen.
3. Accumulate provisions into chunks until adding the next provision would
   exceed ``max_chars``.  Aim for ``target_chars`` per chunk.
4. Overlap: the last ``overlap_chars`` characters of the previous chunk are
   prepended to the next chunk (as a soft context window).
5. Each chunk records:
   - ``chunk_index`` (0-based, within this document run)
   - ``text`` — chunk body
   - ``char_count`` — len(text)
   - ``page_start`` / ``page_end`` — derived from a per-line page map
   - ``hierarchy`` — the JSONB dict from the context at chunk start
   - ``citation_ref`` — human-readable citation at chunk start

Configuration is passed via :class:`ChunkConfig` so all values come from
``Settings`` (no hardcoded constants).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ingestion.extractor import PageRecord
from app.ingestion.hierarchy import HierarchyContext, Level, detect_hierarchy
from app.ingestion.normalizer import normalize_text


@dataclass
class ChunkConfig:
    """Chunk size configuration — should be populated from ``Settings``."""

    target_chars: int = 2000
    max_chars: int = 4000
    overlap_chars: int = 200


@dataclass
class ChunkResult:
    """A single hierarchy-aware text chunk ready for DB persistence."""

    chunk_index: int
    text: str
    char_count: int
    page_start: int | None
    page_end: int | None
    hierarchy: dict[str, Any]
    citation_ref: str | None


# Levels that mark a structural boundary (force a chunk split when possible)
_BOUNDARY_LEVELS = {Level.PART, Level.CHAPTER, Level.SCHEDULE, Level.ARTICLE, Level.SECTION}


def chunk_pages(pages: list[PageRecord], config: ChunkConfig) -> list[ChunkResult]:
    """Chunk a list of extracted pages into hierarchy-aware :class:`ChunkResult` objects.

    Args:
        pages: Output of :func:`~app.ingestion.extractor.extract_pages`.
        config: Size parameters from Settings.

    Returns:
        Ordered list of ``ChunkResult`` instances (0-indexed).
    """
    # ── Build a flat list of (line_text, page_number) ─────────────────────
    line_page_map: list[tuple[str, int]] = []
    for page in pages:
        normalized = normalize_text(page.text)
        for line in normalized.split("\n"):
            line_page_map.append((line, page.page_number))

    if not line_page_map:
        return []

    lines = [lp[0] for lp in line_page_map]
    page_nums = [lp[1] for lp in line_page_map]

    # ── Run hierarchy detection ────────────────────────────────────────────
    labels, contexts = detect_hierarchy(lines)

    # ── Group lines into provisions ────────────────────────────────────────
    # A provision starts at a structural boundary line or the very first line.
    @dataclass
    class Provision:
        lines: list[str] = field(default_factory=list)
        pages: list[int] = field(default_factory=list)
        start_context: HierarchyContext | None = None

    provisions: list[Provision] = []
    current: Provision | None = None

    for i, (line, lbl, ctx) in enumerate(zip(lines, labels, contexts, strict=False)):
        is_boundary = lbl.level in _BOUNDARY_LEVELS

        if current is None or is_boundary:
            current = Provision()
            current.start_context = ctx
            provisions.append(current)

        current.lines.append(line)
        current.pages.append(page_nums[i])

    # ── Accumulate provisions into chunks ─────────────────────────────────
    chunks: list[ChunkResult] = []
    chunk_lines: list[str] = []
    chunk_pages_list: list[int] = []
    chunk_start_ctx: HierarchyContext | None = None
    overlap_tail: str = ""
    chunk_index = 0

    def _flush(
        lines_buf: list[str],
        pages_buf: list[int],
        ctx: HierarchyContext | None,
        prefix: str,
    ) -> ChunkResult:
        body = "\n".join(lines_buf).strip()
        text = (prefix + "\n" + body).strip() if prefix else body
        return ChunkResult(
            chunk_index=chunk_index,
            text=text,
            char_count=len(text),
            page_start=pages_buf[0] if pages_buf else None,
            page_end=pages_buf[-1] if pages_buf else None,
            hierarchy=ctx.as_dict() if ctx else {},
            citation_ref=ctx.build_citation() if ctx else None,
        )

    for prov in provisions:
        prov_text = "\n".join(prov.lines)
        tentative_size = len("\n".join(chunk_lines)) + len(prov_text) + 1

        # If adding this provision exceeds max_chars AND we already have content, flush.
        if chunk_lines and tentative_size > config.max_chars:
            result = _flush(chunk_lines, chunk_pages_list, chunk_start_ctx, overlap_tail)
            chunks.append(result)
            chunk_index += 1

            # Build overlap tail from end of the flushed chunk
            overlap_tail = result.text[-config.overlap_chars :] if config.overlap_chars else ""

            chunk_lines = []
            chunk_pages_list = []
            chunk_start_ctx = prov.start_context

        if not chunk_lines:
            chunk_start_ctx = prov.start_context

        chunk_lines.extend(prov.lines)
        chunk_pages_list.extend(prov.pages)

        # Flush early if we've hit the target
        if len("\n".join(chunk_lines)) >= config.target_chars:
            result = _flush(chunk_lines, chunk_pages_list, chunk_start_ctx, overlap_tail)
            chunks.append(result)
            chunk_index += 1

            overlap_tail = result.text[-config.overlap_chars :] if config.overlap_chars else ""
            chunk_lines = []
            chunk_pages_list = []
            chunk_start_ctx = None

    # Flush any remaining lines
    if chunk_lines:
        result = _flush(chunk_lines, chunk_pages_list, chunk_start_ctx, overlap_tail)
        chunks.append(result)

    # Re-assign chunk_index sequentially (they may already be correct)
    for i, ch in enumerate(chunks):
        ch.chunk_index = i

    return chunks
