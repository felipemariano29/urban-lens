from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


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

    query: str = Field(
        ...,
        description="Natural language search query.",
    )
    filters: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "Optional key/value filters applied to the vector search. "
            "Supported keys: `lsoa_code`, `crime_type`, `reference_month`."
        ),
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return (1–20). Default: 5.")
