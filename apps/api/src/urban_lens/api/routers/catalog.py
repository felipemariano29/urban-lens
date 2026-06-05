from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import require_roles

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Catalog"])


@router.get(
    "/metadata",
    summary="List data catalog entries",
    description=(
        "Returns metadata about datasets registered in the Urban Lens governance catalog. "
        "Fields returned depend on the caller's role:\n\n"
        "- **viewer** — `logical_name`, `layer`\n"
        "- **operator** — adds `version`\n"
        "- **admin** / **internal_service** — adds `id`, `object_path`, `created_at`"
    ),
    responses={
        200: {"description": "Filtered catalog entries."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Insufficient role."},
        502: {"description": "Catalog backend (PostgreSQL) unavailable."},
    },
)
def list_catalog(
    source: Optional[str] = Query(None, description="Filter by dataset logical name."),
    profile: UserProfile = Depends(require_roles("viewer", "operator", "admin", "internal_service")),
) -> List[dict[str, Any]]:
    from urban_lens.api.services import catalog_service

    try:
        return catalog_service.get_metadata(profile=profile, source=source)
    except Exception as exc:
        logger.error("Catalog service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog backend returned an error.",
        )