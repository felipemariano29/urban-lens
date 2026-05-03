from __future__ import annotations

import logging
import time

from urban_lens.api.middleware.correlation import get_correlation_id
from urban_lens.core.settings import AppConfig
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.vector_store import MilvusVectorStore

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_INITIAL_DELAY = 0.5


def _with_retry(func, *args, **kwargs):
    delay = _INITIAL_DELAY
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_ATTEMPTS:
                logger.warning(
                    "RAG call attempt %d/%d failed: %s — retrying in %.1fs | request_id=%s",
                    attempt, _MAX_ATTEMPTS, exc, delay, get_correlation_id(),
                )
                time.sleep(delay)
                delay *= 2
    raise last_exc  # type: ignore[misc]


def run_query(
    query: str,
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    config = AppConfig.from_env()
    embedder = OllamaEmbedder(base_url=config.ollama_base_url, model=config.embedding_model)
    vector_store = MilvusVectorStore(uri=config.milvus_uri)

    t0 = time.perf_counter()
    embeddings = _with_retry(embedder.embed, [query])
    if not embeddings:
        return []

    raw_hits = _with_retry(vector_store.search, query_embedding=embeddings[0], top_k=top_k, filters=filters)
    duration_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "RAG query completed | hits=%d duration_ms=%.1f request_id=%s",
        len(raw_hits), duration_ms, get_correlation_id(),
    )

    results = []
    for hit in raw_hits:
        entity = hit.get("entity", hit)
        results.append(
            {
                "id": str(entity.get("chunk_id", "")),
                "score": float(hit.get("distance", 0.0)),
                "content": str(entity.get("content", "")),
                "metadata": {
                    "chunk_type": entity.get("chunk_type"),
                    "reference_month": entity.get("reference_month"),
                    "lsoa_code": entity.get("lsoa_code"),
                    "crime_type": entity.get("crime_type"),
                    "title": entity.get("title"),
                    "dataset_version_id": entity.get("dataset_version_id"),
                },
            }
        )

    return results