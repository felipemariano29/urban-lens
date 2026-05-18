from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from urban_lens.rag.contracts import EvidenceCitation, RagAnswer, RagContextChunk, AccessProfile, RagTimings


class RunMetricsSchema(BaseModel):
    mae: Optional[float] = Field(None, description="Mean Absolute Error on the holdout partition.")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error on the holdout partition.")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error on the holdout partition.")


class RunMetadataResponse(BaseModel):
    run_id: str = Field(..., description="Unique MLflow run identifier.")
    experiment_id: str = Field(..., description="MLflow experiment identifier.")
    experiment_name: str = Field(..., description="Human-readable experiment name.")
    run_name: Optional[str] = Field(None, description="Optional display name for the run.")
    status: str = Field(..., description="Run lifecycle status (RUNNING, FINISHED, FAILED, KILLED).")
    start_time: Optional[datetime] = Field(None, description="UTC timestamp when the run started.")
    end_time: Optional[datetime] = Field(None, description="UTC timestamp when the run ended.")
    artifact_uri: Optional[str] = Field(None, description="Root URI where run artefacts are stored.")
    metrics: RunMetricsSchema = Field(..., description="Forecast quality metrics logged during training.")
    params: Dict[str, str] = Field(default_factory=dict, description="All key/value parameters logged to the run.")
    dataset_version: Optional[str] = Field(
        None,
        description="Training dataset version extracted from the 'training_dataset_version_id' run parameter.",
    )


class QueryResultMetadata(BaseModel):
    chunk_type: Optional[str] = Field(None, description="Chunk granularity type (e.g. area_month, area_year).")
    reference_month: Optional[str] = Field(None, description="Reference month in YYYY-MM format.")
    lsoa_code: Optional[str] = Field(None, description="Lower Super Output Area code (ONS).")
    crime_type: Optional[str] = Field(None, description="Crime category (e.g. Burglary, Violence).")
    title: Optional[str] = Field(None, description="Human-readable chunk title.")
    dataset_version_id: Optional[str] = Field(None, description="Dataset version this chunk belongs to.")


class QueryResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "chunk-e01001234-2024-01",
                "score": 0.87,
                "content": "In January 2024, Westminster recorded 3 burglaries in LSOA E01001234.",
                "metadata": {
                    "chunk_type": "area_month",
                    "reference_month": "2024-01",
                    "lsoa_code": "E01001234",
                    "crime_type": "Burglary",
                    "title": "Westminster 2024-01",
                    "dataset_version_id": "v1",
                },
            }
        }
    )

    id: str = Field(..., description="Unique chunk identifier.")
    score: float = Field(..., description="Cosine similarity score (0–1; higher is more similar).")
    content: str = Field(..., description="Text content of the evidence chunk.")
    metadata: QueryResultMetadata = Field(..., description="Structured metadata for the chunk.")


class QueryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "id": "chunk-e01001234-2024-01",
                        "score": 0.87,
                        "content": "In January 2024, Westminster recorded 3 burglaries in LSOA E01001234.",
                        "metadata": {
                            "chunk_type": "area_month",
                            "reference_month": "2024-01",
                            "lsoa_code": "E01001234",
                            "crime_type": "Burglary",
                            "title": "Westminster 2024-01",
                            "dataset_version_id": "v1",
                        },
                    }
                ]
            }
        }
    )

    results: List[QueryResult] = Field(..., description="Ranked list of matching evidence chunks.")


class ChatQueryResponse(BaseModel):
    answer: RagAnswer = Field(..., description="Generated RAG answer or governed fallback.")
    evidences: List[EvidenceCitation] = Field(default_factory=list, description="Sources used by the answer.")
    context: List[RagContextChunk] = Field(default_factory=list, description="Retrieved context chunks.")
    profile: AccessProfile = Field(..., description="Normalized access profile applied to the response.")
    fallback_reason: Optional[str] = Field(None, description="Machine-readable fallback reason, when any.")
    timings_ms: RagTimings = Field(..., description="Detailed chat pipeline timings in milliseconds.")


class OllamaModelInfo(BaseModel):
    name: str = Field(..., description="Model name as exposed by the local Ollama catalog.")
    size_bytes: Optional[int] = Field(None, description="Downloaded model size in bytes, when reported by Ollama.")
    digest: Optional[str] = Field(None, description="Immutable model digest, when reported by Ollama.")
    modified_at: Optional[datetime] = Field(None, description="Timestamp of the last model update in Ollama.")


class AvailableModelsResponse(BaseModel):
    default_chat_model: str = Field(..., description="Default chat model used when the client does not select one.")
    default_embedding_model: str = Field(..., description="Embedding model configured for vector search.")
    models: List[OllamaModelInfo] = Field(..., description="Models currently available in the local Ollama runtime.")


class AccessCredentialResponse(BaseModel):
    user_id: str = Field(..., description="Governance user identifier.")
    client_id: str = Field(..., description="Governance API client identifier.")
    api_key_id: str = Field(..., description="Governance API key identifier.")
    role: str = Field(..., description="Application role assigned to the user.")
    plan_code: str = Field(..., description="Service plan code applied to the API client.")
    client_name: str = Field(..., description="Logical API client name.")
    key_prefix: str = Field(..., description="Stored API key prefix used for lookup.")
    api_key: str = Field(..., description="Plaintext API key returned only once at issuance time.")
    expires_at: Optional[datetime] = Field(None, description="Optional API key expiration timestamp.")


class ApiClientInfo(BaseModel):
    client_id: str = Field(..., description="Unique API client identifier.")
    user_id: str = Field(..., description="Owner user identifier.")
    client_name: str = Field(..., description="Logical API client name.")
    status: str = Field(..., description="Client status: active, suspended, or revoked.")
    requests_per_minute_override: Optional[int] = Field(None, description="Client-specific rate limit override.")
    requests_per_day_override: Optional[int] = Field(None, description="Client-specific daily limit override.")
    last_used_at: Optional[datetime] = Field(None, description="Last API key usage timestamp.")
    created_at: datetime = Field(..., description="Client creation timestamp.")
    updated_at: Optional[datetime] = Field(None, description="Last client update timestamp.")
    user_email: str = Field(..., description="Owner email address.")
    user_full_name: str = Field(..., description="Owner display name.")
    user_role: str = Field(..., description="Owner application role.")
    plan_code: str = Field(..., description="Service plan code.")
    plan_name: str = Field(..., description="Service plan display name.")
    plan_requests_per_minute: int = Field(..., description="Plan default rate limit.")
    plan_requests_per_day: int = Field(..., description="Plan default daily limit.")
    active_keys_count: int = Field(..., description="Number of active API keys for this client.")


class ApiClientListResponse(BaseModel):
    clients: List[ApiClientInfo] = Field(..., description="List of API clients.")
    total: int = Field(..., description="Total number of clients returned.")


class ApiKeyInfo(BaseModel):
    api_key_id: str = Field(..., description="Unique API key identifier.")
    client_id: str = Field(..., description="Parent API client identifier.")
    key_prefix: str = Field(..., description="Key prefix for identification (ul_xxxxxx).")
    status: str = Field(..., description="Key status: active, revoked, or expired.")
    expires_at: Optional[datetime] = Field(None, description="Key expiration timestamp.")
    issued_at: datetime = Field(..., description="Key issuance timestamp.")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp.")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp, if revoked.")
    client_name: str = Field(..., description="Parent client name.")
    user_email: str = Field(..., description="Owner email address.")


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyInfo] = Field(..., description="List of API keys.")
    total: int = Field(..., description="Total number of keys returned.")


class ApiKeyRevokeResponse(BaseModel):
    api_key_id: str = Field(..., description="Revoked API key identifier.")
    key_prefix: str = Field(..., description="Revoked key prefix.")
    status: str = Field("revoked", description="New key status after revocation.")
    revoked_at: datetime = Field(..., description="Revocation timestamp.")
    message: str = Field(..., description="Human-readable confirmation message.")


class ApiKeyRotateResponse(BaseModel):
    old_api_key_id: str = Field(..., description="Revoked API key identifier.")
    new_api_key_id: str = Field(..., description="Newly issued API key identifier.")
    client_id: str = Field(..., description="Parent API client identifier.")
    key_prefix: str = Field(..., description="New key prefix for identification.")
    api_key: str = Field(..., description="Plaintext new API key returned only once.")
    expires_at: Optional[datetime] = Field(None, description="New key expiration timestamp.")
    message: str = Field(..., description="Human-readable confirmation message.")


class CurrentUserResponse(BaseModel):
    """Response for GET /api/v1/access/me - current authenticated user info."""

    role: str = Field(..., description="Authenticated user role.")
    auth_type: str = Field(..., description="Authentication method used: jwt, governed_api_key, or internal_api_key.")
    user_id: Optional[str] = Field(None, description="User identifier (for governed API keys).")
    client_id: Optional[str] = Field(None, description="API client identifier (for governed API keys).")
    api_key_id: Optional[str] = Field(None, description="API key identifier (for governed API keys).")
    subject: Optional[str] = Field(None, description="JWT subject claim (for JWT auth).")
    plan_code: Optional[str] = Field(None, description="Service plan code (for governed API keys).")
    plan_max_top_k: Optional[int] = Field(None, description="Maximum top_k allowed by plan.")
    requests_per_minute: Optional[int] = Field(None, description="Rate limit per minute.")
    requests_per_day: Optional[int] = Field(None, description="Rate limit per day.")
    allowed_models: List[str] = Field(default_factory=list, description="Allowed LLM models for chat.")


class UsageStatsResponse(BaseModel):
    """Response for GET /api/v1/access/me/usage - current usage statistics."""

    client_id: str = Field(..., description="API client identifier.")
    requests_last_minute: int = Field(..., description="Requests made in the last minute.")
    requests_last_day: int = Field(..., description="Requests made in the last 24 hours.")
    requests_per_minute_limit: Optional[int] = Field(None, description="Rate limit per minute.")
    requests_per_day_limit: Optional[int] = Field(None, description="Rate limit per day.")
    remaining_minute: Optional[int] = Field(None, description="Remaining requests this minute.")
    remaining_day: Optional[int] = Field(None, description="Remaining requests today.")
