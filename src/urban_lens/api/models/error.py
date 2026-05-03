from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "One or more request fields are invalid.",
                "details": [
                    {
                        "type": "missing",
                        "loc": ["body", "query"],
                        "msg": "Field required",
                    }
                ],
            }
        }
    )

    error: str = Field(
        ...,
        description="Machine-readable error code (e.g. VALIDATION_ERROR, HTTP_401, INTERNAL_ERROR).",
    )
    message: str = Field(..., description="Human-readable summary of the error.")
    details: List[Any] = Field(
        default_factory=list,
        description="Optional list of per-field or contextual details. Empty for most non-validation errors.",
    )
