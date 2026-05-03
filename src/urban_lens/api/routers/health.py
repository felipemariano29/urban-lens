from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from urban_lens.core.settings import AppConfig

logger = logging.getLogger(__name__)
router = APIRouter(tags=["System"])

_VERSION = "0.1.0"


def _check_postgres(config: AppConfig) -> str:
    try:
        import psycopg

        with psycopg.connect(config.postgres_dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return "ok"
    except Exception as exc:
        logger.warning("Postgres health check failed: %s", exc)
        return "unavailable"


def _check_ollama(config: AppConfig) -> str:
    from urban_lens.infrastructure.embedder import OllamaEmbedder

    embedder = OllamaEmbedder(base_url=config.ollama_base_url, model=config.embedding_model)
    return "ok" if embedder.health_check() else "unavailable"


def _check_milvus(config: AppConfig) -> str:
    try:
        from pymilvus import MilvusClient

        client = MilvusClient(uri=config.milvus_uri)
        client.list_collections()
        return "ok"
    except Exception as exc:
        logger.warning("Milvus health check failed: %s", exc)
        return "unavailable"


@router.get(
    "/api/v1/health",
    summary="Liveness and readiness probe",
    description=(
        "Returns API status and the connectivity state of each dependency. "
        "HTTP 200 when all dependencies are healthy; HTTP 207 when at least one is unavailable."
    ),
    responses={
        200: {"description": "All dependencies healthy."},
        207: {"description": "API online but one or more dependencies unavailable."},
    },
)
def health_check() -> JSONResponse:
    config = AppConfig.from_env()

    deps = {
        "catalog": _check_postgres(config),
        "rag_embedder": _check_ollama(config),
        "rag_vector_store": _check_milvus(config),
    }

    all_ok = all(v == "ok" for v in deps.values())

    return JSONResponse(
        status_code=200 if all_ok else 207,
        content={
            "status": "healthy" if all_ok else "degraded",
            "version": _VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dependencies": deps,
        },
    )