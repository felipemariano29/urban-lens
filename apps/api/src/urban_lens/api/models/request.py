from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from urban_lens.rag.contracts import RagFilters


class QueryRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "burglary in Westminster January 2024",
                "filters": {"crime_type": "Burglary", "lsoa_code": "E01001234"},
                "top_k": 5,
            }
        }
    )

    query: str = Field(..., description="Natural language search query.")
    filters: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "Optional key/value filters applied to the vector search. "
            "Supported keys: `lsoa_code`, `crime_type`, `reference_month`."
        ),
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return (1-20). Default: 5.")


class ChatQueryRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Quais evidencias sustentam aumento de burglary em Westminster em 2024-01?",
                "filters": {"lsoa_code": "E01001234", "reference_month": "2024-01", "crime_type": "burglary"},
                "top_k": 5,
                "model": "llama3",
            }
        }
    )

    query: str = Field(..., description="Natural language question for the RAG chat pipeline.")
    filters: RagFilters = Field(default_factory=RagFilters, description="Optional metadata filters.")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks retrieved for context.")
    model: Optional[str] = Field(
        None,
        description="Local Ollama model used for answer generation. Defaults to the configured chat model.",
    )


class AccessCredentialRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Ana Silva",
                "email": "ana.silva@urbanlens.local",
                "organization": "Urban Lens Security Lab",
                "role": "viewer",
                "plan_code": "FREE",
                "client_name": "grafana-demo",
                "expires_at": "2026-12-31T23:59:59Z",
            }
        }
    )

    full_name: str = Field(..., min_length=3, description="Human-readable account owner name.")
    email: str = Field(..., description="Unique user email used for account lookup and ownership.")
    organization: Optional[str] = Field(None, description="Optional organization or team name.")
    role: str = Field("viewer", description="Application role assigned to the user.")
    plan_code: str = Field("FREE", description="Service plan code such as FREE or PRO.")
    client_name: str = Field(..., min_length=3, description="Logical API client name for the issued key.")
    expires_at: Optional[datetime] = Field(None, description="Optional UTC expiration timestamp for the issued key.")


class ApiKeyRevokeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Security incident - key potentially compromised",
            }
        }
    )

    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason for revoking the API key.",
    )


class ApiKeyRotateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "expires_at": "2027-06-30T23:59:59Z",
            }
        }
    )

    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration timestamp for the new rotated key.",
    )


class AccessRequestCreateRequest(BaseModel):
    """Public request model for access onboarding."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John Doe",
                "email": "john.doe@example.com",
                "organization": "City Intelligence Office",
                "use_case": "Need read-only analytics access for monthly urban safety reviews.",
            }
        }
    )

    full_name: str = Field(..., min_length=3, max_length=100, description="Full name of the requester.")
    email: str = Field(..., description="Email address for follow-up and approval flow.")
    organization: str | None = Field(None, max_length=120, description="Optional organization or department.")
    use_case: str = Field(..., min_length=10, max_length=800, description="Why the requester needs access.")
