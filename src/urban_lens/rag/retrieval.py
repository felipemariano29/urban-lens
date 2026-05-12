"""Retrieval and context assembly for the Urban Lens RAG pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from urban_lens.rag.access import filter_context
from urban_lens.rag.contracts import AccessProfile, RagContextChunk, RagFilters


def _score_from_hit(hit: dict[str, Any]) -> float:
    raw = hit.get("distance", hit.get("score", 0.0))
    try:
        score = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _metadata_from_entity(entity: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "chunk_type",
        "reference_month",
        "lsoa_code",
        "crime_type",
        "title",
        "dataset_version_id",
        "run_id",
        "experiment_id",
        "artifact_uri",
        "metrics",
        "params",
    )
    return {key: entity.get(key) for key in keys if key in entity and entity.get(key) not in (None, "")}


def milvus_hits_to_context(raw_hits: list[dict[str, Any]], profile: AccessProfile) -> list[RagContextChunk]:
    chunks: list[RagContextChunk] = []
    for hit in raw_hits:
        entity = hit.get("entity", hit)
        metadata = _metadata_from_entity(entity)
        chunk_id = str(entity.get("chunk_id") or entity.get("id") or "")
        title = str(entity.get("title") or metadata.get("chunk_type") or "Urban Lens evidence")
        dataset_version_id = str(entity.get("dataset_version_id") or "unknown")
        reference_month = str(entity.get("reference_month") or "")
        reference = dataset_version_id if not reference_month else f"{dataset_version_id}:{reference_month}"
        chunks.append(
            RagContextChunk(
                id=chunk_id,
                content=str(entity.get("content") or ""),
                score=_score_from_hit(hit),
                source=title,
                reference=reference,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata,
            )
        )
    return filter_context(chunks, profile)


def build_context_text(chunks: list[RagContextChunk], max_chars: int) -> str:
    blocks: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks, start=1):
        block = (
            f"[E{index}] source={chunk.source}; reference={chunk.reference}; "
            f"score={chunk.score:.3f}; timestamp={chunk.timestamp.isoformat()}\n"
            f"{chunk.content}"
        )
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def filters_to_vector_store(filters: RagFilters, profile: AccessProfile) -> dict[str, str]:
    return filters.to_milvus_filters(profile)
