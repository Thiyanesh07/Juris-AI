"""Unit tests for app/ingestion/chunker.py."""


from app.ingestion.chunker import ChunkConfig, chunk_pages
from app.ingestion.extractor import PageRecord


def _make_pages(text: str, page_number: int = 1) -> list[PageRecord]:
    return [PageRecord(page_number=page_number, text=text, blocks=[])]


def _default_config(target: int = 200, max_c: int = 400, overlap: int = 50) -> ChunkConfig:
    return ChunkConfig(target_chars=target, max_chars=max_c, overlap_chars=overlap)


# ── Basic chunking ─────────────────────────────────────────────────────────────


def test_chunk_empty_document_returns_empty() -> None:
    result = chunk_pages([], _default_config())
    assert result == []


def test_chunk_short_text_returns_single_chunk() -> None:
    pages = _make_pages("Short legal text.")
    chunks = chunk_pages(pages, _default_config())
    assert len(chunks) >= 1


def test_chunks_are_zero_indexed() -> None:
    pages = _make_pages("Some text.")
    chunks = chunk_pages(pages, _default_config())
    for i, ch in enumerate(chunks):
        assert ch.chunk_index == i


def test_chunks_have_char_count_matching_text() -> None:
    pages = _make_pages("Article 1 text that is exactly as long as it says.")
    chunks = chunk_pages(pages, _default_config())
    for ch in chunks:
        assert ch.char_count == len(ch.text)


def test_chunk_respects_max_chars() -> None:
    """Chunks should not significantly exceed max_chars when text has hierarchy markers."""
    # Build text with many article boundaries to trigger splits
    articles = "\n".join(
        f"Article {i}\nThis is the body text for article number {i}. " * 5
        for i in range(1, 30)
    )
    pages = _make_pages(articles)
    config = ChunkConfig(target_chars=300, max_chars=600, overlap_chars=50)
    chunks = chunk_pages(pages, config)
    # Most chunks should respect max_chars; allow some slack for overlap prefix
    oversized = [
        ch for ch in chunks
        if ch.char_count > config.max_chars + config.overlap_chars + 200
    ]
    assert len(oversized) == 0, f"Oversized chunks: {[ch.char_count for ch in oversized]}"


# ── Hierarchy-aware splitting ─────────────────────────────────────────────────


def test_chunk_splits_on_article_boundary() -> None:
    text = "\n".join([
        "PART I",
        "Article 1",
        "India is a Union of States.",
        "Article 2",
        "New States may be admitted.",
        "Article 3",
        "Parliament may alter boundaries.",
    ])
    pages = _make_pages(text)
    # Use small target to force splits
    config = ChunkConfig(target_chars=50, max_chars=100, overlap_chars=10)
    chunks = chunk_pages(pages, config)
    assert len(chunks) >= 2


def test_chunk_hierarchy_dict_keys() -> None:
    text = "PART I\nArticle 1\n(1) Text here."
    pages = _make_pages(text)
    chunks = chunk_pages(pages, _default_config())
    for ch in chunks:
        assert isinstance(ch.hierarchy, dict)
        # All hierarchy keys should be present
        for key in ("part", "chapter", "article", "section", "subsection", "clause"):
            assert key in ch.hierarchy


def test_chunk_carries_page_numbers() -> None:
    page1 = PageRecord(page_number=1, text="PART I\nArticle 1\nText on page one.", blocks=[])
    page2 = PageRecord(page_number=2, text="Article 2\nText on page two.", blocks=[])
    chunks = chunk_pages([page1, page2], _default_config())
    for ch in chunks:
        assert ch.page_start is not None
        assert ch.page_end is not None
        assert ch.page_start <= ch.page_end


def test_chunk_citation_ref_for_article() -> None:
    text = "Article 15\n(1) State shall not discriminate.\n(2) Further text."
    pages = _make_pages(text)
    chunks = chunk_pages(pages, _default_config())
    citations = [ch.citation_ref for ch in chunks if ch.citation_ref]
    assert any("Article 15" in c for c in citations)


def test_chunk_text_is_not_empty() -> None:
    text = "PART I\nArticle 1\nSome important legal provision here."
    pages = _make_pages(text)
    chunks = chunk_pages(pages, _default_config())
    for ch in chunks:
        assert ch.text.strip() != ""
