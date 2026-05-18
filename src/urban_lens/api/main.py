from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from urban_lens.api.middleware.correlation import CorrelationIdMiddleware
from urban_lens.api.middleware.request_audit import RequestAuditMiddleware
from urban_lens.api.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from urban_lens.api.router import register_routers
from urban_lens.core.settings import AppConfig

_TAGS_METADATA = [
    {
        "name": "System",
        "description": (
            "Health and readiness probes. "
            "**No authentication required.** "
            "Returns `200` when all dependencies are healthy or `207` when at least one is degraded."
        ),
    },
    {
        "name": "Query",
        "description": (
            "Semantic similarity search over indexed crime evidence chunks (Milvus vector store). "
            "`/api/v1/query` returns ranked chunks; `/api/v1/chat/query` also generates a "
            "local Ollama answer with evidence citations and role-filtered context. "
            "Requires a valid JWT or API Key. Accessible to **all authenticated roles**."
        ),
    },
    {
        "name": "Access",
        "description": (
            "Governed access-management endpoints for issuing API credentials tied to service plans. "
            "Restricted to `admin` and `internal_service`."
        ),
    },
    {
        "name": "Catalog",
        "description": (
            "Governance data catalog listing registered datasets. "
            "Field visibility is role-controlled: `viewer` sees public fields only; "
            "`operator` adds `version`; `admin` and `internal_service` add technical fields."
        ),
    },
    {
        "name": "MLflow Metadata",
        "description": (
            "MLflow training run metadata for the Urban Lens forecast pipeline. "
            "Restricted to **`admin`** and **`internal_service`** roles."
        ),
    },
    {
        "name": "Internal",
        "description": (
            "Internal operational endpoints. "
            "Restricted to `admin` and `internal_service`. "
            "Hidden from the public OpenAPI schema."
        ),
    },
]

app = FastAPI(
    title="Urban Lens API",
    version="0.1.0",
    description=(
        "REST API for the **Urban Lens** urban security intelligence platform.\n\n"
        "Provides semantic crime data search, a role-governed data catalog, "
        "and MLflow governance metadata for the forecast pipeline.\n\n"
        "## Authentication\n\n"
        "All endpoints except `/api/v1/health` require authentication via one of:\n\n"
        "- **Bearer JWT** — `Authorization: Bearer <token>` — payload must include a `role` claim "
        "(`viewer`, `operator`, `intel_user`, `developer`, `admin`, or `internal_service`).\n"
        "- **API Key** — `X-API-Key: <key>` — grants `internal_service` role; "
        "configured via the `URBAN_LENS_INTERNAL_API_KEY` environment variable.\n\n"
        "## Error format\n\n"
        "All errors follow a standard envelope:\n"
        "```json\n"
        '{"error": "HTTP_403", "message": "...", "details": []}\n'
        "```\n\n"
        "See `docs/rbac.md` for the full role matrix and field visibility rules."
    ),
    openapi_tags=_TAGS_METADATA,
    contact={"name": "Urban Lens Team", "email": "lucasclaudetcc@gmail.com"},
    license_info={"name": "MIT"},
)

_config = AppConfig.from_env()

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

register_routers(app)
