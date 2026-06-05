"""Shared contracts for governance, medallion layout, and chat responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

BRONZE_LAYER = "bronze"
SILVER_LAYER = "silver"
GOLD_LAYER = "gold"

GOLD_RAG_PRODUCT = "gold/rag/crime_chunks"
GOLD_ANALYTICS_AREA_MONTH = "gold/analytics/crime_metrics_area_month"
GOLD_ANALYTICS_AREA_MONTH_CATEGORY = "gold/analytics/crime_metrics_area_month_category"
GOLD_ANALYTICS_MONTH_CATEGORY = "gold/analytics/crime_metrics_month_category"
GOLD_ML_TRAINING = "gold/ml/forecast_training_set"
GOLD_ML_SCORING = "gold/ml/forecast_scoring_set"
GOLD_ML_PREDICTIONS = "gold/ml/forecast_predictions"

MODEL_NAME = "crime_count_forecaster"
MODEL_TARGET = "incident_count_next_period"
MODEL_FEATURE_COLUMNS = [
    "incident_count_current_period",
    "incident_count_lag_1",
    "incident_count_lag_2",
    "incident_count_lag_3",
    "moving_avg_3",
    "moving_avg_6",
    "trend_lag1_vs_lag3",
    "crime_type",
    "lsoa_code",
    "month_number",
    "quarter",
    "has_previous_outcome_ratio",
    "missing_context_ratio",
]

CSV_COLUMN_ALIASES = {
    "crime_id": "crime_id",
    "reported_by": "reported_by",
    "falls_within": "falls_within",
    "longitude": "longitude",
    "latitude": "latitude",
    "lsoa_code": "lsoa_code",
    "lsoa_name": "lsoa_name",
    "crime_type": "crime_type",
    "last_outcome_category": "last_outcome_category",
    "context": "context",
    "month": "month",
    "location": "location",
}

SILVER_OUTPUT_COLUMNS = [
    "crime_id",
    "reference_month",
    "reported_by",
    "falls_within",
    "longitude",
    "latitude",
    "location",
    "lsoa_code",
    "lsoa_name",
    "crime_type",
    "last_outcome_category",
    "context",
    "has_outcome",
    "has_context",
    "source_file",
    "ingested_at",
    "record_hash",
]

SUPPORTED_POLICE_UK_DATASET_KIND = "street"

GOVERNANCE_EVENT_TYPES = {
    "ingest_started",
    "ingest_finished",
    "validation_failed",
    "transform_started",
    "transform_finished",
    "gold_published",
    "model_training_started",
    "model_training_finished",
    "model_inference_requested",
    "model_inference_completed",
    "embedding_indexing_started",
    "embedding_indexing_finished",
}

CHAT_QUERY_TYPES = {
    "factual_past_or_present",
    "predictive_future",
    "mixed",
}


class GovernancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DatasetVersionPayload(GovernancePayload):
    source_name: str
    layer: str
    logical_name: str
    version: str
    schema_version: str
    object_path: str
    row_count: int
    content_hash: str
    valid_from: str | None = None
    valid_to: str | None = None
    status: str = "available"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PipelineRunPayload(GovernancePayload):
    pipeline_name: str
    run_type: str
    status: str
    triggered_by: str
    input_versions: list[str] = Field(default_factory=list)
    output_versions: list[str] = Field(default_factory=list)
    error_summary: str | None = None


class AuditEventPayload(GovernancePayload):
    event_type: str
    actor: str
    object_type: str
    object_id: str
    details_json: dict[str, Any] = Field(default_factory=dict)


class ModelVersionPayload(GovernancePayload):
    model_name: str
    model_version: str
    target_name: str
    training_dataset_version_id: str
    scoring_dataset_version_id: str
    training_window_start: str
    training_window_end: str
    metrics_json: dict[str, Any]
    artifact_uri: str
    status: str = "ready"


class GovernedUserPayload(GovernancePayload):
    full_name: str
    email: str
    organization: str | None = None
    role: str = "viewer"
    status: str = "active"


class ApiClientPayload(GovernancePayload):
    user_id: str
    plan_code: str
    client_name: str
    status: str = "active"
    requests_per_minute_override: int | None = None
    requests_per_day_override: int | None = None


class ApiKeyPayload(GovernancePayload):
    client_id: str
    key_prefix: str
    key_hash: str
    status: str = "active"
    expires_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AccessRequestPayload(GovernancePayload):
    full_name: str
    email: str
    organization: str | None = None
    use_case: str
    requested_plan_code: str = "FREE"
    status: str = "pending_review"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RequestAuditPayload(GovernancePayload):
    request_id: str
    route_path: str
    http_method: str
    user_id: str | None = None
    client_id: str | None = None
    api_key_id: str | None = None
    plan_id: str | None = None
    response_status: int | None = None
    model_name: str | None = None
    latency_ms: float | None = None
    remote_ip: str | None = None
    user_agent: str | None = None
    filters_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime | None = None
