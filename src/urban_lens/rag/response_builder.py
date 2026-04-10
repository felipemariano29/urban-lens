"""Build user-facing chat responses from retrieval context and generated text."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from urban_lens.rag.fallback import apply_low_confidence_warning
from urban_lens.rag.schemas import (
    ChatResponse,
    CitationEvidence,
    EvidenceSummary,
    FactualResponse,
    RetrievalContext,
    SourceReference,
)


def _build_citation_snippet(content: str, max_len: int = 250) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


class ResponseBuilder:
    def build_factual_response(
        self,
        *,
        query: str,
        retrieval_context: RetrievalContext,
        generated_answer: str,
        model_used: str,
        source_references: list[SourceReference],
        audit_id: UUID | None = None,
    ) -> ChatResponse:
        sorted_chunks = sorted(retrieval_context.chunks, key=lambda chunk: chunk.relevance_score, reverse=True)
        citations = [
            CitationEvidence(
                chunk_id=chunk.chunk_id,
                snippet=_build_citation_snippet(chunk.content),
                relevance_score=chunk.relevance_score,
                crime_type=chunk.crime_type,
                reference_month=chunk.reference_month,
                url=f"/api/v1/evidence/{chunk.chunk_id}",
            )
            for chunk in sorted_chunks[:3]
        ]

        scores = [chunk.relevance_score for chunk in sorted_chunks]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        evidence_summary = EvidenceSummary(
            total_chunks_used=len(sorted_chunks),
            min_relevance_score=min_score,
            max_relevance_score=max_score,
            sources=source_references,
            citations=citations,
            data_lineage_summary=(
                "Dados de data.police.uk processados em Bronze/Silver e publicados na camada Gold com versionamento."
            ),
        )

        factual = FactualResponse(
            answer=generated_answer,
            confidence_score=mean_score,
            evidence_summary=evidence_summary,
            query_intent=retrieval_context.query_intent,
            time_window=retrieval_context.coverage_period,
            geographic_scope=retrieval_context.geographic_scope,
            generation_timestamp=datetime.now(timezone.utc),
            model_used=model_used,
        )

        factual = apply_low_confidence_warning(factual)

        return ChatResponse(success=True, response=factual, failure=None, audit_id=audit_id or uuid4())
