from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field

from urban_lens.rag.contracts import QueryIntent
from urban_lens.rag.schemas import ChatResponse


class RunMetricsSchema(BaseModel):
    mae: Optional[float] = Field(None, description="Mean Absolute Error on the holdout partition.")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error on the holdout partition.")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error on the holdout partition.")


class RunMetadataResponse(BaseModel):
    run_id: str = Field(..., description="Unique MLflow run identifier.")
    experiment_id: str = Field(..., description="MLflow experiment ID that owns this run.")
    experiment_name: str = Field(..., description="Human-readable experiment name.")
    run_name: Optional[str] = Field(None, description="Optional display name of the run.")
    status: str = Field(..., description="Run lifecycle status (RUNNING, FINISHED, FAILED, KILLED).")
    start_time: Optional[datetime] = Field(None, description="UTC timestamp when the run started.")
    end_time: Optional[datetime] = Field(None, description="UTC timestamp when the run ended.")
    artifact_uri: Optional[str] = Field(None, description="Root URI where run artefacts (models, plots) are stored.")
    metrics: RunMetricsSchema = Field(..., description="Forecast quality metrics logged during training.")
    params: Dict[str, str] = Field(default_factory=dict, description="All key/value parameters logged to the run.")
    dataset_version: Optional[str] = Field(
        None,
        description="Training dataset version extracted from the 'training_dataset_version_id' run parameter.",
    )


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=3)
    query_intent: QueryIntent | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class ChatQueryResponse(BaseModel):
    result: ChatResponse
