"""Text cleaning: fix hyphenation, normalize whitespace, drop repeated headers/footers."""
from __future__ import annotations

import re
from collections import Counter


def clean_text(text: str) -> str:
    """Normalize parsed text (single page or document)."""
    if not text:
        return ""
    # join words split across line breaks: "inform-\nation" -> "information"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # collapse runs of spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    # strip trailing spaces per line
    text = "\n".join(line.strip() for line in text.splitlines())
    # collapse 3+ blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_repeated_lines(pages: list[str], min_repeat: int = 3) -> list[str]:
    """Remove boilerplate lines (headers/footers) that recur across many pages.

    A short line appearing on >= min_repeat pages is treated as boilerplate.
    """
    if len(pages) < min_repeat:
        return pages
    counts: Counter[str] = Counter()
    for p in pages:
        for line in {ln.strip() for ln in p.splitlines() if ln.strip()}:
            if len(line) < 80:  # only short lines are header/footer candidates
                counts[line] += 1
    boiler = {ln for ln, c in counts.items() if c >= min_repeat}
    if not boiler:
        return pages
    return [
        "\n".join(ln for ln in p.splitlines() if ln.strip() not in boiler)
        for p in pages
    ]
