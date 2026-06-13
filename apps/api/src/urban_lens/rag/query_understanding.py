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
    "platform_knowledge",
    "generic",
]

# Corpus selection based on query intent
CorpusSelection = Literal["crime", "knowledge", "hybrid"]

LSOA_CODE_PATTERN = re.compile(r"\b[EW]010\d{5}\b", re.IGNORECASE)
REFERENCE_MONTH_PATTERN = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])\b")


def detect_query_intent(question: str) -> QueryIntent:
    normalized = _normalized_text(question)

    # Platform/MLflow knowledge queries
    platform_markers = {
        "urban lens",
        "urban-lens",
        "quem e voce",
        "o que voce faz",
        "o que e o urban lens",
        "what are you",
        "who are you",
        "what do you do",
        "mlflow",
        "ml flow",
        "experimento",
        "experiment",
        "modelo treinado",
        "modelos treinados",
        "quais modelos foram treinados",
        "trained model",
        "trained models",
        "forecast model",
        "modelo de previsao",
        "como funciona",
        "how does it work",
        "arquitetura",
        "architecture",
        "pipeline",
        "api endpoint",
        "documentacao",
        "documentation",
        "metricas do modelo",
        "metricas foram utilizadas",
        "metricas foram usadas",
        "quais metricas foram utilizadas",
        "model metrics",
        "hyperparameters",
        "hiperparametros",
        "pre-processamento",
        "pre processamento",
        "preprocessamento",
        "qual foi o pre-processamento realizado nos dados",
        "data preprocessing",
        "run id",
        "artifact",
        "artefato",
    }
    if any(marker in normalized for marker in platform_markers):
        return "platform_knowledge"

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


def intent_to_corpus(intent: QueryIntent) -> CorpusSelection:
    """Map a query intent to the appropriate corpus selection strategy.

    Returns:
        "crime" - Search only crime_chunks collection
        "knowledge" - Search only knowledge_chunks collection
        "hybrid" - Search both collections and merge results
    """
    if intent == "platform_knowledge":
        return "knowledge"

    # Crime-specific intents
    if intent in ("crime_type_listing", "dominant_crime", "comparison"):
        return "crime"

    # Generic queries may benefit from both corpora
    return "hybrid"


def preferred_knowledge_filters(question: str) -> dict[str, str] | None:
    normalized = _normalized_text(question)
    faq_markers = {
        "quem e voce",
        "who are you",
        "what are you",
        "o que voce faz",
        "quais modelos foram treinados",
        "trained models",
        "modelos treinados",
        "metricas foram utilizadas",
        "model metrics",
        "pre-processamento",
        "pre processamento",
        "preprocessamento",
        "data preprocessing",
    }
    if any(marker in normalized for marker in faq_markers):
        return {"source_type": "docs", "document_category": "platform"}
    return None
