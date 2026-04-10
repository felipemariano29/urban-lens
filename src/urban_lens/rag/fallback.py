"""Fallback helpers for low-confidence RAG answers."""

from __future__ import annotations

from urban_lens.rag.contracts import LOW_CONFIDENCE_THRESHOLD
from urban_lens.rag.schemas import FactualResponse, TemporalComparisonResponse


LOW_CONFIDENCE_WARNING_MESSAGE = (
    "Resposta gerada com baixa confianca por evidencia limitada ou baixa relevancia dos dados recuperados."
)


def apply_low_confidence_warning(
    response: FactualResponse | TemporalComparisonResponse,
    *,
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> FactualResponse | TemporalComparisonResponse:
    if response.confidence_score >= threshold:
        return response

    payload = response.model_dump()
    payload["low_confidence_warning"] = True
    payload["warning_message"] = LOW_CONFIDENCE_WARNING_MESSAGE
    return type(response)(**payload)
