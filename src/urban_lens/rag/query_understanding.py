"""Lightweight query understanding helpers for local RAG behavior."""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from urban_lens.rag.contracts import RagFilters, RagQuery

QueryIntent = Literal[
    "crime_type_listing",
    "dominant_crime",
    "comparison",
    "generic",
]

LSOA_CODE_PATTERN = re.compile(r"\b[EW]010\d{5}\b", re.IGNORECASE)
REFERENCE_MONTH_PATTERN = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])\b")


def detect_query_intent(question: str) -> QueryIntent:
    normalized = _normalized_text(question)

    if any(marker in normalized for marker in {" compare ", " compar", " versus ", " vs "}):
        return "comparison"

    listing_markers = {
        "quais tipos de crime",
        "quais crimes",
        "what crime types",
        "which crime types",
        "what crimes",
        "which crimes",
        "tipos de crime registrados",
        "crimes registrados",
        "crime categories",
    }
    if any(marker in normalized for marker in listing_markers):
        return "crime_type_listing"

    dominant_markers = {
        "crime dominante",
        "tipo de crime dominante",
        "crime mais comum",
        "tipo de crime com mais ocorrencias",
        "tipo de crime com mais ocorrencias",
        "dominant crime type",
        "most common crime",
    }
    if any(marker in normalized for marker in dominant_markers):
        return "dominant_crime"

    return "generic"


def enrich_filters_from_question(request: RagQuery) -> RagFilters:
    """Merge explicit filters with safe metadata inferred from the question text."""

    filters = request.filters.model_copy(deep=True)
    inferred_lsoa = infer_lsoa_code(request.query)
    inferred_month = infer_reference_month(request.query)

    if inferred_lsoa and not filters.lsoa_code and not filters.region:
        filters.lsoa_code = inferred_lsoa
    if inferred_month and not filters.reference_month and not filters.period:
        filters.reference_month = inferred_month
    return filters


def infer_lsoa_code(question: str) -> str | None:
    match = LSOA_CODE_PATTERN.search(question)
    if not match:
        return None
    return match.group(0).upper()


def infer_reference_month(question: str) -> str | None:
    match = REFERENCE_MONTH_PATTERN.search(question)
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}"


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return f" {' '.join(ascii_text.lower().split())} "
