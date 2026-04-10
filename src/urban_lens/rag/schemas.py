"""Pydantic schemas for RAG retrieval context, evidence/citations, and responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from urban_lens.rag.contracts import ChunkType, FailureType, QueryIntent, RetrievalMethod


class RAGModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetrievedChunk(RAGModel):
    chunk_id: str
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    chunk_type: ChunkType = ChunkType.AREA_MONTH_CATEGORY
    lsoa_code: str | None = None
    crime_type: str
    reference_month: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}$")
    dataset_version_id: UUID
    source_path: str


class RetrievalContext(RAGModel):
    query: str
    query_intent: QueryIntent
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    coverage_period: str
    geographic_scope: str | None = None
    total_chunks_indexed: int = Field(ge=0)
    retrieval_method: RetrievalMethod
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retrieval_latency_ms: float = Field(ge=0)


class SourceReference(RAGModel):
    dataset_version_id: UUID
    logical_name: str
    version: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}$")
    layer: Literal["gold"] = "gold"
    gold_product: str
    reference_month: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}$")
    row_count: int = Field(ge=0)
    content_hash: str
    valid_from: datetime


class CitationEvidence(RAGModel):
    chunk_id: str
    snippet: Annotated[str, Field(min_length=1, max_length=250)]
    relevance_score: float = Field(ge=0.0, le=1.0)
    crime_type: str
    reference_month: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}$")
    url: str | None = None


class EvidenceSummary(RAGModel):
    total_chunks_used: int = Field(ge=0)
    min_relevance_score: float = Field(ge=0.0, le=1.0)
    max_relevance_score: float = Field(ge=0.0, le=1.0)
    sources: list[SourceReference] = Field(default_factory=list)
    citations: list[CitationEvidence] = Field(default_factory=list)
    data_lineage_summary: str


class FactualResponse(RAGModel):
    answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    low_confidence_warning: bool = False
    warning_message: str | None = None
    evidence_summary: EvidenceSummary
    query_intent: QueryIntent
    time_window: str
    geographic_scope: str | None = None
    generation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str


class TemporalComparisonPeriod(RAGModel):
    period: str
    key_findings: str


class TemporalDelta(RAGModel):
    trend: str
    percentage_change: float


class TemporalComparisonResponse(RAGModel):
    answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    low_confidence_warning: bool = False
    warning_message: str | None = None
    period_1: TemporalComparisonPeriod
    period_2: TemporalComparisonPeriod
    delta: TemporalDelta
    evidence_summary: EvidenceSummary
    generation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FailureResponse(RAGModel):
    error_type: FailureType
    error_message: str
    suggestion: str | None = None
    fallback_attempted: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatResponse(RAGModel):
    success: bool
    response: FactualResponse | TemporalComparisonResponse | None = None
    failure: FailureResponse | None = None
    audit_id: UUID
