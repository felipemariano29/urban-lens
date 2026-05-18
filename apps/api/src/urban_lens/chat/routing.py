"""Heuristic query routing for factual and predictive chat requests."""

from __future__ import annotations

import re


PREDICTIVE_PATTERNS = (
    r"\bforecast\b",
    r"\bprediction\b",
    r"\bpredict\b",
    r"\bnext month\b",
    r"\bnext period\b",
    r"\bfuture\b",
    r"\bwill increase\b",
    r"\bestimate\b",
)


def classify_query_intent(question: str) -> str:
    normalized = question.strip().lower()
    predictive_matches = any(re.search(pattern, normalized) for pattern in PREDICTIVE_PATTERNS)
    historical_matches = any(
        token in normalized for token in ("last month", "current", "historical", "increase", "most frequent")
    )

    if predictive_matches and historical_matches:
        return "mixed"
    if predictive_matches:
        return "predictive_future"
    return "factual_past_or_present"
