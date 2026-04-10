"""Canonical contracts for RAG context retrieval, evidence, and response generation."""

from __future__ import annotations

from enum import StrEnum


class QueryIntent(StrEnum):
    FACTUAL = "factual"
    TEMPORAL_COMPARISON = "temporal_comparison"
    TREND_FORECAST = "trend_forecast"


class RetrievalMethod(StrEnum):
    MILVUS_SEMANTIC = "milvus_semantic"
    POSTGRES_STRUCTURED = "postgres_structured"
    HYBRID = "hybrid"


class ChunkType(StrEnum):
    AREA_MONTH_CATEGORY = "area_month_category"
    TREND = "trend"
    COMPARISON = "comparison"


class FailureType(StrEnum):
    INSUFFICIENT_RELEVANCE = "insufficient_relevance"
    NO_DATA_MATCHING = "no_data_matching"
    QUERY_PARSE_ERROR = "query_parse_error"


MIN_RELEVANCE_SCORE = 0.50
TOP_K_DEFAULT = 5
LOW_CONFIDENCE_THRESHOLD = 0.50
