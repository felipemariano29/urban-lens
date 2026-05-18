"""Canonical RAG contracts shared by retrieval, generation, and API layers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AccessProfile(str, Enum):
    """Profiles supported by the chat contract.

    The project still accepts the earlier API roles (`viewer`, `operator`,
    `internal_service`). They are normalized before reaching the pipeline.
    """

    intel_user = "intel_user"
    developer = "developer"
    admin = "admin"


class RagFilters(BaseModel):
    """Metadata filters accepted by the retrieval layer."""

    region: str | None = Field(None, description="Area filter; mapped to lsoa_code when it looks like an LSOA.")
    lsoa_code: str | None = Field(None, description="Lower Super Output Area code.")
    reference_month: str | None = Field(None, description="Reference month in YYYY-MM format.")
    period: str | None = Field(None, description="Alias for reference_month.")
    crime_type: str | None = Field(None, description="Crime category filter.")
    chunk_type: str | None = Field(None, description="Chunk type filter, only honoured for technical profiles.")

    def to_milvus_filters(self, profile: AccessProfile) -> dict[str, str]:
        allowed: dict[str, str] = {}
        lsoa_code = self.lsoa_code or self.region
        reference_month = self.reference_month or self.period

        if lsoa_code:
            allowed["lsoa_code"] = lsoa_code
        if reference_month:
            allowed["reference_month"] = reference_month
        if self.crime_type:
            allowed["crime_type"] = self.crime_type
        if self.chunk_type and profile in {AccessProfile.developer, AccessProfile.admin}:
            allowed["chunk_type"] = self.chunk_type
        return allowed


class RagQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language user question.")
    top_k: int = Field(5, ge=1, le=20, description="Number of retrieved chunks.")
    filters: RagFilters = Field(default_factory=RagFilters, description="Structured metadata filters.")
    profile: AccessProfile = Field(AccessProfile.intel_user, description="Access profile used to shape context.")
    model: str = Field(..., description="Local Ollama generation model.")
    min_score: float = Field(0.15, ge=0.0, le=1.0, description="Minimum similarity score for enough evidence.")
    max_context_chars: int = Field(6000, ge=500, le=20000, description="Prompt context budget in characters.")


class RagContextChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique context chunk id.")
    content: str = Field(..., description="Evidence text sent to the prompt.")
    score: float = Field(..., description="Similarity score normalized to 0-1 where possible.")
    source: str = Field(..., description="Logical source or title for citation.")
    reference: str = Field(..., description="Stable reference to dataset/document/run.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict, description="Role-filtered metadata.")


class EvidenceCitation(BaseModel):
    id: str = Field(..., description="Citation id used in the generated answer, e.g. E1.")
    source: str = Field(..., description="Human-readable source title.")
    reference: str = Field(..., description="Stable data reference.")
    score: float = Field(..., description="Similarity score for this evidence.")
    timestamp: datetime = Field(..., description="Timestamp when the evidence was assembled.")
    excerpt: str = Field(..., description="Short excerpt used as supporting evidence.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Role-filtered metadata.")


class RagAnswer(BaseModel):
    text: str = Field(..., description="Generated answer or governed fallback message.")
    status: Literal["answered", "insufficient_evidence"] = Field(..., description="Answer confidence state.")
    model: str = Field(..., description="Local Ollama model used for generation.")


class RagResponse(BaseModel):
    answer: RagAnswer
    evidences: list[EvidenceCitation] = Field(default_factory=list)
    context: list[RagContextChunk] = Field(default_factory=list)
    profile: AccessProfile
    fallback_reason: str | None = None
