from __future__ import annotations

from fastapi import APIRouter, Depends

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import require_roles

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get(
    "/status",
    summary="Internal system status",
    include_in_schema=False,
)
def internal_status(
    profile: UserProfile = Depends(require_roles("admin", "internal_service")),
) -> dict:
    return {"status": "ok", "role": profile.role}