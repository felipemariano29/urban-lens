from pydantic import BaseModel
from typing import Dict, Optional

class RunMetadataResponse(BaseModel):
    run_id: str
    experiment_id: str
    run_name: str
    status: str
    metrics: Dict[str, float]
    dataset_version: Optional[str] = None