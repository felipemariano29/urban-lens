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
