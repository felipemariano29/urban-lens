from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from urban_lens.rag.contracts import QueryIntent
from urban_lens.rag.fallback import LOW_CONFIDENCE_WARNING_MESSAGE, apply_low_confidence_warning
from urban_lens.rag.response_builder import ResponseBuilder
from urban_lens.rag.schemas import (
    EvidenceSummary,
    FactualResponse,
    RetrievalContext,
    RetrievedChunk,
    SourceReference,
)


def _sample_source_reference() -> SourceReference:
    return SourceReference(
        dataset_version_id=uuid4(),
        logical_name="crime_chunks",
        version="2024-01",
        gold_product="gold/rag/crime_chunks",
        reference_month="2024-01",
        row_count=120,
        content_hash="abc123",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _sample_chunk(score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{int(score * 100)}",
        content="In 2024-01, Westminster recorded 5 burglary incidents and 1 robbery incident.",
        relevance_score=score,
        crime_type="burglary",
        reference_month="2024-01",
        dataset_version_id=uuid4(),
        source_path="s3://urban-lens/gold/rag/crime_chunks/year=2024/month=01/part-000.parquet",
        lsoa_code="E01004736",
    )


def test_retrieved_chunk_serialization() -> None:
    chunk = _sample_chunk(0.89)

    payload = chunk.model_dump()

    assert payload["relevance_score"] == 0.89
    assert payload["reference_month"] == "2024-01"


def test_retrieval_context_serialization() -> None:
    context = RetrievalContext(
        query="Quais crimes aumentaram em Westminster?",
        query_intent=QueryIntent.FACTUAL,
        chunks=[_sample_chunk(0.8), _sample_chunk(0.6)],
        coverage_period="2024-01 a 2024-02",
        geographic_scope="Westminster",
        total_chunks_indexed=300,
        retrieval_method="hybrid",
        retrieval_latency_ms=12.5,
    )

    assert context.total_chunks_indexed == 300
    assert len(context.chunks) == 2


def test_low_confidence_warning_on_low_score() -> None:
    response = FactualResponse(
        answer="Aparentemente houve aumento de burglary em janeiro.",
        confidence_score=0.42,
        evidence_summary=EvidenceSummary(
            total_chunks_used=1,
            min_relevance_score=0.42,
            max_relevance_score=0.42,
            sources=[_sample_source_reference()],
            citations=[],
            data_lineage_summary="lineage",
        ),
        query_intent=QueryIntent.FACTUAL,
        time_window="2024-01 a 2024-01",
        model_used="ollama-mistral-7b",
    )

    updated = apply_low_confidence_warning(response)

    assert updated.low_confidence_warning is True
    assert updated.warning_message == LOW_CONFIDENCE_WARNING_MESSAGE


def test_response_builder_creates_valid_factual_response() -> None:
    context = RetrievalContext(
        query="Quais crimes aumentaram em Westminster?",
        query_intent=QueryIntent.FACTUAL,
        chunks=[_sample_chunk(0.91), _sample_chunk(0.73), _sample_chunk(0.65)],
        coverage_period="2024-01 a 2024-03",
        geographic_scope="Westminster",
        total_chunks_indexed=550,
        retrieval_method="hybrid",
        retrieval_latency_ms=10.0,
    )
    builder = ResponseBuilder()

    chat_response = builder.build_factual_response(
        query=context.query,
        retrieval_context=context,
        generated_answer="Burglary apresentou maior crescimento no periodo.",
        model_used="ollama-mistral-7b",
        source_references=[_sample_source_reference()],
    )

    assert chat_response.success is True
    assert chat_response.failure is None
    assert chat_response.response is not None
    assert chat_response.response.evidence_summary.total_chunks_used == 3
    assert len(chat_response.response.evidence_summary.citations) == 3
