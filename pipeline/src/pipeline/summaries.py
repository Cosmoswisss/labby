"""Deterministic cleanup of LLM summaries.

The model sometimes writes about the page instead of the project ("The page gives only the
title.", "The page lists it as an available master semester project."). Those sentences
are dropped; the rest of the summary is kept. Used by the export (so existing data is fixed
without re-extraction) and by the evaluation (to count remaining issues).
"""

from __future__ import annotations

import re

META_SUMMARY_RE = re.compile(
    r"\b(the page|this page|the website|the listing|page (gives|provides|lists|only)|"
    r"(is |are )?listed as|lists it|no (further |additional )?(details|description|"
    r"information)|not (provided|specified|described|stated)|only (the )?title|title only|"
    r"details are not|not mentioned)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def is_meta(text: str) -> bool:
    return bool(META_SUMMARY_RE.search(text or ""))


def clean_summary(summary: str) -> str:
    """Removes sentences about the page / missing information; keeps the rest."""
    sentences = _SENTENCE_SPLIT_RE.split((summary or "").strip())
    kept = [s for s in sentences if s and not is_meta(s)]
    return " ".join(kept).strip()


def count_meta(projects: list[dict]) -> int:
    return sum(1 for p in projects if is_meta(p.get("summary") or ""))
