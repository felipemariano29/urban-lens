"""Role normalization and context filtering rules for RAG chat."""

from __future__ import annotations

from typing import Any

from urban_lens.rag.contracts import AccessProfile, RagContextChunk

ROLE_TO_PROFILE = {
    "viewer": AccessProfile.intel_user,
    "operator": AccessProfile.intel_user,
    "intel_user": AccessProfile.intel_user,
    "developer": AccessProfile.developer,
    "admin": AccessProfile.admin,
    "internal_service": AccessProfile.admin,
}

TECHNICAL_CHUNK_TYPES = {"documentation", "experiment_metadata", "mlflow_run"}
SENSITIVE_METADATA_KEYS = {
    "artifact_uri",
    "prompt",
    "prompt_template",
    "system_prompt",
    "raw_params",
    "params",
    "metrics",
    "run_id",
    "experiment_id",
}


def normalize_profile(role: str) -> AccessProfile:
    return ROLE_TO_PROFILE.get(role, AccessProfile.intel_user)


def is_chunk_authorized(raw_metadata: dict[str, Any], profile: AccessProfile) -> bool:
    chunk_type = str(raw_metadata.get("chunk_type") or "").lower()
    if chunk_type in TECHNICAL_CHUNK_TYPES and profile == AccessProfile.intel_user:
        return False
    return True


def filter_metadata(raw_metadata: dict[str, Any], profile: AccessProfile) -> dict[str, Any]:
    visible: dict[str, Any] = {}
    for key, value in raw_metadata.items():
        if value in (None, ""):
            continue
        if profile == AccessProfile.intel_user and key in SENSITIVE_METADATA_KEYS:
            continue
        if profile == AccessProfile.developer and key in {"artifact_uri", "prompt", "prompt_template", "system_prompt"}:
            continue
        visible[key] = value
    return visible


def filter_context(chunks: list[RagContextChunk], profile: AccessProfile) -> list[RagContextChunk]:
    filtered: list[RagContextChunk] = []
    for chunk in chunks:
        if not is_chunk_authorized(chunk.metadata, profile):
            continue
        filtered.append(chunk.model_copy(update={"metadata": filter_metadata(chunk.metadata, profile)}))
    return filtered
