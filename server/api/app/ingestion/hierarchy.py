"""Legal hierarchy detector — identifies structural markers in Indian legal texts.

Recognises the following hierarchy levels (in descending precedence):

  PART       → "PART I", "PART XIV-A", "Part One"
  CHAPTER    → "CHAPTER III", "Chapter 4"
  SCHEDULE   → "FIRST SCHEDULE", "THE SECOND SCHEDULE", "SCHEDULE I"
  ARTICLE    → "Article 15", "ARTICLE 370"
  SECTION    → "Section 3", "SECTION 14A"
  SUBSECTION → "(1)", "(2A)"  (parenthetical digit sequence at line start)
  CLAUSE     → "(a)", "(b)"  (parenthetical lowercase letter)
  SUB_CLAUSE → "(i)", "(ii)" (parenthetical Roman numeral)
  PROVISO    → lines starting with "Provided that", "Provided further"
  EXPLANATION → lines starting with "Explanation", "Explanation.—"
  EXCEPTION  → lines starting with "Exception"

Each line of the document is labelled with a :class:`HierarchyLabel` and the
running :class:`HierarchyContext` is updated so every chunk can carry its full
ancestry (Part → Chapter → Article/Section → …).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any


class Level(enum.StrEnum):
    """Hierarchy levels in ascending specificity order."""

    PART = "part"
    CHAPTER = "chapter"
    SCHEDULE = "schedule"
    ARTICLE = "article"
    SECTION = "section"
    SUBSECTION = "subsection"
    CLAUSE = "clause"
    SUB_CLAUSE = "sub_clause"
    PROVISO = "proviso"
    EXPLANATION = "explanation"
    EXCEPTION = "exception"
    TEXT = "text"  # plain body text — no structural marker


@dataclass
class HierarchyLabel:
    """A single line annotated with its structural level."""

    level: Level
    marker: str  # e.g. "XIV-A", "15", "(2)", "(a)", "(ii)"
    text: str  # the full original line


@dataclass
class HierarchyContext:
    """Running breadcrumb of the current position within the document structure."""

    part: str | None = None
    chapter: str | None = None
    schedule: str | None = None
    article: str | None = None
    section: str | None = None
    subsection: str | None = None
    clause: str | None = None
    sub_clause: str | None = None
    proviso: bool = False
    explanation: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict for storage in the ``hierarchy`` JSONB column."""
        return {
            "part": self.part,
            "chapter": self.chapter,
            "schedule": self.schedule,
            "article": self.article,
            "section": self.section,
            "subsection": self.subsection,
            "clause": self.clause,
            "sub_clause": self.sub_clause,
            "proviso": self.proviso,
            "explanation": self.explanation,
        }

    def build_citation(self) -> str | None:
        """Build a human-readable citation reference string from context.

        Examples:
          ``"Article 15(2)(a)"``
          ``"Section 3(1)(b)(i)"``
          ``"Part XIV-A, Chapter I"``
        """
        parts: list[str] = []
        if self.article:
            ref = f"Article {self.article}"
            if self.subsection:
                ref += f"({self.subsection})"
            if self.clause:
                ref += f"({self.clause})"
            if self.sub_clause:
                ref += f"({self.sub_clause})"
            parts.append(ref)
        elif self.section:
            ref = f"Section {self.section}"
            if self.subsection:
                ref += f"({self.subsection})"
            if self.clause:
                ref += f"({self.clause})"
            if self.sub_clause:
                ref += f"({self.sub_clause})"
            parts.append(ref)

        if not parts:
            if self.part:
                parts.append(f"Part {self.part}")
            if self.chapter:
                parts.append(f"Chapter {self.chapter}")
            if self.schedule:
                parts.append(f"Schedule {self.schedule}")

        return ", ".join(parts) if parts else None

    def reset_below(self, level: Level) -> None:
        """Reset all levels more specific than *level* when a new ancestor is set."""
        order = [
            Level.PART,
            Level.CHAPTER,
            Level.SCHEDULE,
            Level.ARTICLE,
            Level.SECTION,
            Level.SUBSECTION,
            Level.CLAUSE,
            Level.SUB_CLAUSE,
        ]
        if level not in order:
            return
        idx = order.index(level)
        for lvl in order[idx + 1 :]:
            match lvl:
                case Level.CHAPTER:
                    self.chapter = None
                case Level.SCHEDULE:
                    self.schedule = None
                case Level.ARTICLE:
                    self.article = None
                case Level.SECTION:
                    self.section = None
                case Level.SUBSECTION:
                    self.subsection = None
                case Level.CLAUSE:
                    self.clause = None
                case Level.SUB_CLAUSE:
                    self.sub_clause = None
        self.proviso = False
        self.explanation = False


# ── Compiled regex patterns ────────────────────────────────────────────────────

_RE_PART = re.compile(
    r"^(?:THE\s+)?PART\s+([IVXLCDM]+(?:-[A-Z])?|[A-Z]{1,3}|\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)\b",
    re.IGNORECASE,
)
_RE_CHAPTER = re.compile(
    r"^(?:THE\s+)?CHAPTER\s+([IVXLCDM]+|\d+|[A-Z])\b",
    re.IGNORECASE,
)
_RE_SCHEDULE = re.compile(
    r"^(?:THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|[IVXLCDM]+|[A-Z]+|\d+)?\s*SCHEDULE\b",
    re.IGNORECASE,
)
_RE_ARTICLE = re.compile(
    r"^(?:ARTICLE|Art\.?)\s+(\d+[A-Z]?(?:-[A-Z])?)\b",
    re.IGNORECASE,
)
_RE_SECTION = re.compile(
    r"^(?:SECTION|Sec\.?)\s+(\d+[A-Z]?(?:-[A-Z])?)\b",
    re.IGNORECASE,
)
_RE_SUBSECTION = re.compile(r"^\((\d+[A-Z]?)\)\s")
_RE_CLAUSE = re.compile(r"^\(([a-z]{1,2})\)\s")
_RE_SUB_CLAUSE = re.compile(r"^\((i{1,3}|iv|vi{0,3}|ix|xi{0,2}|x[iv]*)\)\s", re.IGNORECASE)
_RE_PROVISO = re.compile(r"^Provided\s+(?:further\s+)?that\b", re.IGNORECASE)
_RE_EXPLANATION = re.compile(r"^Explanation\s*[\.\—\-]?", re.IGNORECASE)
_RE_EXCEPTION = re.compile(r"^Exception\s*[\.\—\-]?", re.IGNORECASE)


def label_line(line: str) -> HierarchyLabel:
    """Classify a single *line* and return a :class:`HierarchyLabel`."""
    stripped = line.strip()
    if not stripped:
        return HierarchyLabel(level=Level.TEXT, marker="", text=line)

    if m := _RE_PART.match(stripped):
        return HierarchyLabel(level=Level.PART, marker=m.group(1).upper(), text=line)
    if m := _RE_CHAPTER.match(stripped):
        return HierarchyLabel(level=Level.CHAPTER, marker=m.group(1).upper(), text=line)
    if m := _RE_SCHEDULE.match(stripped):
        marker = (m.group(1) or "").strip().upper() or "SCHEDULE"
        return HierarchyLabel(level=Level.SCHEDULE, marker=marker, text=line)
    if m := _RE_ARTICLE.match(stripped):
        return HierarchyLabel(level=Level.ARTICLE, marker=m.group(1), text=line)
    if m := _RE_SECTION.match(stripped):
        return HierarchyLabel(level=Level.SECTION, marker=m.group(1), text=line)
    if _RE_PROVISO.match(stripped):
        return HierarchyLabel(level=Level.PROVISO, marker="proviso", text=line)
    if _RE_EXPLANATION.match(stripped):
        return HierarchyLabel(level=Level.EXPLANATION, marker="explanation", text=line)
    if _RE_EXCEPTION.match(stripped):
        return HierarchyLabel(level=Level.EXCEPTION, marker="exception", text=line)
    # Sub-clause before clause so "(iv)" matches sub_clause not clause
    if m := _RE_SUB_CLAUSE.match(stripped):
        return HierarchyLabel(level=Level.SUB_CLAUSE, marker=m.group(1).lower(), text=line)
    if m := _RE_CLAUSE.match(stripped):
        return HierarchyLabel(level=Level.CLAUSE, marker=m.group(1), text=line)
    if m := _RE_SUBSECTION.match(stripped):
        return HierarchyLabel(level=Level.SUBSECTION, marker=m.group(1), text=line)
    return HierarchyLabel(level=Level.TEXT, marker="", text=line)


def detect_hierarchy(
    lines: list[str],
) -> tuple[list[HierarchyLabel], list[HierarchyContext]]:
    """Annotate every line and return parallel lists of labels and contexts.

    Returns ``(labels, contexts)`` where ``contexts[i]`` holds the hierarchy
    state *after* processing ``labels[i]``.
    """
    ctx = HierarchyContext()
    labels: list[HierarchyLabel] = []
    contexts: list[HierarchyContext] = []

    for line in lines:
        lbl = label_line(line)
        labels.append(lbl)

        match lbl.level:
            case Level.PART:
                ctx.reset_below(Level.PART)
                ctx.part = lbl.marker
            case Level.CHAPTER:
                ctx.reset_below(Level.CHAPTER)
                ctx.chapter = lbl.marker
            case Level.SCHEDULE:
                ctx.reset_below(Level.SCHEDULE)
                ctx.schedule = lbl.marker
            case Level.ARTICLE:
                ctx.reset_below(Level.ARTICLE)
                ctx.article = lbl.marker
            case Level.SECTION:
                ctx.reset_below(Level.SECTION)
                ctx.section = lbl.marker
            case Level.SUBSECTION:
                ctx.reset_below(Level.SUBSECTION)
                ctx.subsection = lbl.marker
            case Level.CLAUSE:
                ctx.reset_below(Level.CLAUSE)
                ctx.clause = lbl.marker
            case Level.SUB_CLAUSE:
                ctx.sub_clause = lbl.marker
            case Level.PROVISO:
                ctx.proviso = True
                ctx.explanation = False
            case Level.EXPLANATION:
                ctx.explanation = True
                ctx.proviso = False
            case Level.EXCEPTION:
                pass  # no state change beyond marking text

        # Snapshot the current context (shallow copy via field replacement)
        import copy

        contexts.append(copy.copy(ctx))

    return labels, contexts
