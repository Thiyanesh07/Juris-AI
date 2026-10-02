"""Text normalizer — cleans extracted PDF text without destroying legal identifiers.

Conservative strategy:
- Normalize line endings to ``\\n``
- Collapse sequences of blank lines to a single blank line
- Strip trailing whitespace from each line
- Merge hyphenated line-breaks (``word-\\n`` → ``word``)
- Collapse runs of spaces/tabs within a line to a single space
- Preserve all legal identifiers: Article/Section/Clause numbers, parenthetical
  markers like ``(1)``, ``(a)``, ``(i)``, Roman numerals, etc.
- Do NOT strip any legal keyword (Part, Chapter, Proviso, Explanation, Schedule…)

The input is a single string (the full page or document text); the output is a
cleaned string ready for hierarchy detection and chunking.
"""

import re

# ── Compiled patterns ──────────────────────────────────────────────────────────

# Hyphenated line-break: "constitu-\ntion" → "constitution"
_HYPHEN_BREAK = re.compile(r"-\n(?=[a-zA-Z])")

# Multiple blank lines → single blank line
_MULTI_BLANK = re.compile(r"\n{3,}")

# Trailing whitespace on each line
_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)

# Leading whitespace that's not meaningful indentation (more than 4 spaces → 0)
_EXCESSIVE_INDENT = re.compile(r"^[ \t]{5,}", re.MULTILINE)

# Multiple spaces / tabs within a line → single space
_INLINE_MULTI_SPACE = re.compile(r"[ \t]{2,}")

# Windows-style line endings
_CRLF = re.compile(r"\r\n|\r")


def normalize_text(text: str) -> str:
    """Clean *text* for downstream processing.

    Applies normalizations in a fixed order so each step sees the result of
    the previous one.  Legal identifiers are preserved verbatim.
    """
    if not text:
        return ""

    # 1. Normalize line endings
    text = _CRLF.sub("\n", text)

    # 2. Merge hyphenated line-breaks before touching whitespace
    text = _HYPHEN_BREAK.sub("", text)

    # 3. Strip trailing whitespace per line
    text = _TRAILING_WS.sub("", text)

    # 4. Collapse excessive leading indentation (>4 spaces becomes flush)
    text = _EXCESSIVE_INDENT.sub("", text)

    # 5. Collapse inline runs of spaces/tabs to single space
    text = _INLINE_MULTI_SPACE.sub(" ", text)

    # 6. Collapse 3+ consecutive blank lines to a single blank line
    text = _MULTI_BLANK.sub("\n\n", text)

    return text.strip()
