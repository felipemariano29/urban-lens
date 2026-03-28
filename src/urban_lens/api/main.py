from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import get_db
from .schemas import RunMetadataResponse

app = FastAPI(
    title="Urban Lens Internal API",
    description="Internal API for MLflow metadata queries and governance.",
    version="0.1.0"
)

@app.get("/api/v1/metadata/runs", response_model=List[RunMetadataResponse], tags=["MLflow Metadata"])
def list_runs(
    experiment_id: Optional[str] = Query(None, description="Filter by MLflow experiment ID"),
    dataset: Optional[str] = Query(None, description="Filter by dataset name or version"),
    db: Session = Depends(get_db)
):
    mock_run = RunMetadataResponse(
        run_id="fake-run-123",
        experiment_id=experiment_id or "default-exp",
        run_name="baseline-model-run",
        status="FINISHED",
        metrics={"mae": 1.5, "rmse": 2.1},
        dataset_version=dataset or "2024-01"
    )
    return [mock_run]

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "online"}