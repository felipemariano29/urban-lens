from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from urban_lens.api.middleware.correlation import CorrelationIdMiddleware
from urban_lens.api.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from urban_lens.api.middleware.metrics import MetricsMiddleware, metrics_endpoint
from urban_lens.api.middleware.request_audit import RequestAuditMiddleware
from urban_lens.api.router import register_routers
from urban_lens.core.settings import AppConfig

_TAGS_METADATA = [
    {
        "name": "System",
        "description": (
            "Health, readiness and onboarding endpoints. "
            "Public probing remains available through `/api/v1/health`, while public access onboarding is "
            "available through `/api/v1/system/access-requests`."
        ),
    },
    {
        "name": "Query",
        "description": (
            "Semantic similarity search over indexed evidence plus full governed RAG generation. "
            "Requires a valid JWT or governed API key."
        ),
    },
    {
        "name": "Access",
        "description": (
            "Governed access-management endpoints for issuing, rotating and inspecting credentials tied to service plans. "
            "Administrative operations are restricted to trusted roles."
        ),
    },
    {
        "name": "Catalog",
        "description": (
            "Governance data catalog listing registered datasets with role-based field visibility."
        ),
    },
    {
        "name": "MLflow Metadata",
        "description": (
            "MLflow run metadata for the Urban Lens forecast and evaluation workflows."
        ),
    },
    {
        "name": "Internal",
        "description": (
            "Internal operational endpoints hidden from the public OpenAPI schema."
        ),
    },
]

app = FastAPI(
    title="Urban Lens API",
    version="0.1.0",
    description=(
        "REST API for the Urban Lens urban security intelligence platform.\n\n"
        "Provides semantic crime data search, governed access control, governance metadata and MLflow run metadata.\n\n"
        "## Authentication\n\n"
        "All endpoints except `/api/v1/health` and `/api/v1/system/access-requests` require authentication via one of:\n\n"
        "- **Bearer JWT**: `Authorization: Bearer <token>` with a `role` claim.\n"
        "- **Governed API Key**: `X-API-Key: <key>` resolved against the governance store, including plan and quota.\n"
        "- **Internal service key**: `X-API-Key: <key>` reserved for machine-to-machine operations through "
        "`URBAN_LENS_INTERNAL_API_KEY`.\n\n"
        "## Error format\n\n"
        "All errors follow a standard envelope:\n"
        "```json\n"
        '{"error": "HTTP_403", "message": "...", "details": []}\n'
        "```\n\n"
        "See `docs/rbac.md` for the role matrix and field-visibility rules."
    ),
    openapi_tags=_TAGS_METADATA,
    contact={"name": "Urban Lens Team", "email": "lucasclaudetcc@gmail.com"},
    license_info={"name": "MIT"},
)

_config = AppConfig.from_env()

app.add_middleware(MetricsMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestAuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

register_routers(app)
