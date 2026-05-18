from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import require_roles
from urban_lens.api.schemas import AccessCredentialRequest, AccessCredentialResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/access", tags=["Access"])


@router.post(
    "/credentials",
    response_model=AccessCredentialResponse,
    summary="Create a governed API access credential",
    description=(
        "Creates or updates a governed user, provisions an API client bound to a FREE or PRO plan, "
        "and issues a plaintext API key. The plaintext key is returned only once."
    ),
    responses={
        200: {"description": "Access credential issued successfully."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Authenticated caller lacks permission to issue credentials."},
        422: {"description": "Invalid input payload."},
    },
)
def create_access_credential(
    body: AccessCredentialRequest,
    _profile: UserProfile = Depends(require_roles("admin", "internal_service")),
) -> AccessCredentialResponse:
    from urban_lens.api.services import access_service

    try:
        return access_service.issue_access_credential(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Access credential issuance failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access governance backend returned an error.",
        )
