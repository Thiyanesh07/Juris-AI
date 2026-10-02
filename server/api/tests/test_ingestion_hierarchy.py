"""Unit tests for app/ingestion/hierarchy.py."""

from app.ingestion.hierarchy import (
    HierarchyContext,
    Level,
    detect_hierarchy,
    label_line,
)

# ── label_line unit tests ─────────────────────────────────────────────────────


def test_label_part_roman() -> None:
    lbl = label_line("PART XIV-A")
    assert lbl.level == Level.PART
    assert lbl.marker == "XIV-A"


def test_label_part_word() -> None:
    lbl = label_line("PART ONE")
    assert lbl.level == Level.PART


def test_label_chapter() -> None:
    lbl = label_line("CHAPTER III")
    assert lbl.level == Level.CHAPTER
    assert lbl.marker == "III"


def test_label_article() -> None:
    lbl = label_line("Article 15")
    assert lbl.level == Level.ARTICLE
    assert lbl.marker == "15"


def test_label_article_with_letter() -> None:
    lbl = label_line("Article 370A")
    assert lbl.level == Level.ARTICLE
    assert lbl.marker == "370A"


def test_label_section() -> None:
    lbl = label_line("Section 3")
    assert lbl.level == Level.SECTION
    assert lbl.marker == "3"


def test_label_subsection() -> None:
    lbl = label_line("(1) The State shall not deny to any person")
    assert lbl.level == Level.SUBSECTION
    assert lbl.marker == "1"


def test_label_clause() -> None:
    lbl = label_line("(a) equality before the law")
    assert lbl.level == Level.CLAUSE
    assert lbl.marker == "a"


def test_label_sub_clause_roman() -> None:
    lbl = label_line("(ii) the right to education")
    assert lbl.level == Level.SUB_CLAUSE
    assert lbl.marker == "ii"


def test_label_proviso() -> None:
    lbl = label_line("Provided that nothing in this article shall apply")
    assert lbl.level == Level.PROVISO


def test_label_proviso_further() -> None:
    lbl = label_line("Provided further that the state may make special provisions")
    assert lbl.level == Level.PROVISO


def test_label_explanation() -> None:
    lbl = label_line("Explanation.— For the purposes of this article")
    assert lbl.level == Level.EXPLANATION


def test_label_schedule() -> None:
    lbl = label_line("FIRST SCHEDULE")
    assert lbl.level == Level.SCHEDULE


def test_label_the_schedule() -> None:
    lbl = label_line("THE SECOND SCHEDULE")
    assert lbl.level == Level.SCHEDULE


def test_label_plain_text() -> None:
    lbl = label_line("India is a sovereign socialist secular democratic republic.")
    assert lbl.level == Level.TEXT


def test_label_empty_line() -> None:
    lbl = label_line("")
    assert lbl.level == Level.TEXT


# ── detect_hierarchy integration tests ────────────────────────────────────────


def test_detect_hierarchy_updates_context() -> None:
    lines = [
        "PART I",
        "CHAPTER I",
        "Article 1",
        "(1) India, that is Bharat, shall be a Union of States.",
        "(a) the territories of the States;",
    ]
    labels, contexts = detect_hierarchy(lines)
    assert len(labels) == len(contexts) == len(lines)

    # After PART I
    assert contexts[0].part == "I"

    # After CHAPTER I
    assert contexts[1].chapter == "I"
    assert contexts[1].part == "I"

    # After Article 1
    assert contexts[2].article == "1"

    # After subsection (1)
    assert contexts[3].subsection == "1"

    # After clause (a)
    assert contexts[4].clause == "a"


def test_detect_hierarchy_resets_on_new_part() -> None:
    lines = [
        "PART I",
        "CHAPTER I",
        "Article 1",
        "PART II",
    ]
    _, contexts = detect_hierarchy(lines)
    # After PART II, chapter and article should be cleared
    assert contexts[3].part == "II"
    assert contexts[3].chapter is None
    assert contexts[3].article is None


def test_detect_hierarchy_resets_on_new_article() -> None:
    lines = [
        "Article 1",
        "(1) First subsection",
        "(a) first clause",
        "Article 2",
    ]
    _, contexts = detect_hierarchy(lines)
    ctx_after_art2 = contexts[3]
    assert ctx_after_art2.article == "2"
    assert ctx_after_art2.subsection is None
    assert ctx_after_art2.clause is None


# ── HierarchyContext.build_citation ───────────────────────────────────────────


def test_build_citation_article_with_subsection_and_clause() -> None:
    ctx = HierarchyContext(part="III", article="15", subsection="2", clause="a")
    citation = ctx.build_citation()
    assert citation is not None
    assert "Article 15" in citation
    assert "(2)" in citation
    assert "(a)" in citation


def test_build_citation_section_only() -> None:
    ctx = HierarchyContext(section="3")
    citation = ctx.build_citation()
    assert citation == "Section 3"


def test_build_citation_empty_context() -> None:
    ctx = HierarchyContext()
    citation = ctx.build_citation()
    assert citation is None


def test_build_citation_part_chapter_fallback() -> None:
    ctx = HierarchyContext(part="I", chapter="II")
    citation = ctx.build_citation()
    assert citation is not None
    assert "Part I" in citation
    assert "Chapter II" in citation
