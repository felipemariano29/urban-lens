from __future__ import annotations

import logging
import time
from typing import Any

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.middleware.correlation import get_correlation_id
from urban_lens.core.settings import AppConfig
from urban_lens.governance.store import MetadataStore

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
                    "Catalog call attempt %d/%d failed: %s — retrying in %.1fs | request_id=%s",
                    attempt, _MAX_ATTEMPTS, exc, delay, get_correlation_id(),
                )
                time.sleep(delay)
                delay *= 2
    raise last_exc  # type: ignore[misc]


def get_metadata(
    profile: UserProfile,
    source: str | None = None,
) -> list[dict[str, Any]]:
    config = AppConfig.from_env()
    store = MetadataStore(dsn=config.postgres_dsn)

    t0 = time.perf_counter()
    rows = _with_retry(store.list_dataset_versions, logical_name=source)
    duration_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "Catalog query completed | rows=%d duration_ms=%.1f request_id=%s",
        len(rows), duration_ms, get_correlation_id(),
    )

    result: list[dict[str, Any]] = []
    for row in rows:
        entry: dict[str, Any] = {
            "logical_name": row["logical_name"],
            "layer": row["layer"],
        }

        if profile.role in {"operator", "admin", "internal_service"}:
            entry["version"] = row["version"]

        if profile.role in {"admin", "internal_service"}:
            entry["id"] = str(row["id"])
            entry["object_path"] = row["object_path"]
            entry["created_at"] = row["created_at"].isoformat() if row["created_at"] else None

        result.append(entry)

    return result