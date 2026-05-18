from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import require_roles
from urban_lens.api.schemas import (
    AccessCredentialRequest,
    AccessCredentialResponse,
    ApiClientListResponse,
    ApiKeyListResponse,
    ApiKeyRevokeRequest,
    ApiKeyRevokeResponse,
    ApiKeyRotateRequest,
    ApiKeyRotateResponse,
)

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


@router.get(
    "/clients",
    response_model=ApiClientListResponse,
    summary="List API clients",
    description=(
        "Returns a list of API clients with their plan information, rate limits, and key counts. "
        "Optionally filter by user_id or include inactive clients."
    ),
    responses={
        200: {"description": "API clients listed successfully."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Authenticated caller lacks permission to list clients."},
    },
)
def list_clients(
    user_id: Optional[str] = Query(None, description="Filter by owner user ID."),
    include_inactive: bool = Query(False, description="Include suspended or revoked clients."),
    _profile: UserProfile = Depends(require_roles("admin", "operator", "internal_service")),
) -> ApiClientListResponse:
    from urban_lens.api.services import access_service

    try:
        return access_service.list_api_clients(user_id=user_id, include_inactive=include_inactive)
    except Exception as exc:
        logger.error("Failed to list API clients: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access governance backend returned an error.",
        )


@router.get(
    "/keys",
    response_model=ApiKeyListResponse,
    summary="List API keys",
    description=(
        "Returns a list of API keys with their status, usage timestamps, and parent client information. "
        "Optionally filter by client_id or include revoked keys."
    ),
    responses={
        200: {"description": "API keys listed successfully."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Authenticated caller lacks permission to list keys."},
    },
)
def list_keys(
    client_id: Optional[str] = Query(None, description="Filter by parent API client ID."),
    include_revoked: bool = Query(False, description="Include revoked keys in the response."),
    _profile: UserProfile = Depends(require_roles("admin", "operator", "internal_service")),
) -> ApiKeyListResponse:
    from urban_lens.api.services import access_service

    try:
        return access_service.list_api_keys(client_id=client_id, include_revoked=include_revoked)
    except Exception as exc:
        logger.error("Failed to list API keys: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access governance backend returned an error.",
        )


@router.post(
    "/keys/{api_key_id}/revoke",
    response_model=ApiKeyRevokeResponse,
    summary="Revoke an API key",
    description=(
        "Permanently revokes an API key. The key cannot be used after revocation. "
        "Use this when a key is compromised or no longer needed."
    ),
    responses={
        200: {"description": "API key revoked successfully."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Authenticated caller lacks permission to revoke keys."},
        404: {"description": "API key not found."},
        422: {"description": "API key already revoked or invalid state."},
    },
)
def revoke_key(
    api_key_id: str,
    body: Optional[ApiKeyRevokeRequest] = None,
    _profile: UserProfile = Depends(require_roles("admin", "operator", "internal_service")),
) -> ApiKeyRevokeResponse:
    from urban_lens.api.services import access_service

    try:
        return access_service.revoke_api_key(api_key_id, body)
    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)
    except Exception as exc:
        logger.error("Failed to revoke API key: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access governance backend returned an error.",
        )


@router.post(
    "/keys/{api_key_id}/rotate",
    response_model=ApiKeyRotateResponse,
    summary="Rotate an API key",
    description=(
        "Rotates an API key by revoking the old key and issuing a new one for the same client. "
        "The new plaintext key is returned only once. Use this for regular key rotation."
    ),
    responses={
        200: {"description": "API key rotated successfully. New key returned."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Authenticated caller lacks permission to rotate keys."},
        404: {"description": "API key not found."},
        422: {"description": "API key not active or cannot be rotated."},
    },
)
def rotate_key(
    api_key_id: str,
    body: Optional[ApiKeyRotateRequest] = None,
    _profile: UserProfile = Depends(require_roles("admin", "operator", "internal_service")),
) -> ApiKeyRotateResponse:
    from urban_lens.api.services import access_service

    try:
        return access_service.rotate_api_key(api_key_id, body)
    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)
    except Exception as exc:
        logger.error("Failed to rotate API key: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access governance backend returned an error.",
        )
