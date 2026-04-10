from __future__ import annotations

from fastapi import FastAPI

from urban_lens.api.routers import metadata

app = FastAPI(
    title="Urban Lens Internal API",
    description=(
        "Internal API for structured MLflow metadata queries and governance. "
        "All endpoints require a valid `x-profile-name` header for RBAC enforcement."
    ),
    version="0.1.0",
)

app.include_router(metadata.router)


@app.get("/health", tags=["System"], summary="Liveness probe")
def health_check() -> dict[str, str]:
    return {"status": "online"}