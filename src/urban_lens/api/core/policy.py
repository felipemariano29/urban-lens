from __future__ import annotations

from fastapi import HTTPException, status

from urban_lens.api.core.auth import UserProfile
from urban_lens.core.settings import AppConfig


def enforce_plan_top_k(profile: UserProfile, requested_top_k: int) -> None:
    if profile.plan_max_top_k is None:
        return
    if requested_top_k <= profile.plan_max_top_k:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"Plan limit exceeded: top_k={requested_top_k} is not allowed for plan "
            f"'{profile.plan_code or 'unknown'}'. Maximum allowed: {profile.plan_max_top_k}."
        ),
    )


def resolve_chat_model(profile: UserProfile, requested_model: str | None) -> str:
    resolved_model = requested_model or AppConfig.from_env().chat_model
    if not profile.allowed_models:
        return resolved_model
    if resolved_model in profile.allowed_models:
        return resolved_model
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"Model '{resolved_model}' is not allowed for plan '{profile.plan_code or 'unknown'}'. "
            f"Allowed models: {sorted(profile.allowed_models)}."
        ),
    )
