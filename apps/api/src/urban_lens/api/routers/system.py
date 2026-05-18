from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import require_roles
from urban_lens.api.schemas import (
    AccessRequestCreateRequest,
    AccessRequestCreateResponse,
    AvailableModelsResponse,
    OllamaModelInfo,
)
from urban_lens.core.settings import AppConfig
from urban_lens.governance import AccessRequestPayload, MetadataStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/system", tags=["System"])


def _fetch_ollama_models(config: AppConfig) -> list[OllamaModelInfo]:
    request = urllib.request.Request(f"{config.ollama_base_url.rstrip('/')}/api/tags", method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return [
        OllamaModelInfo(
            name=model["name"],
            size_bytes=model.get("size"),
            digest=model.get("digest"),
            modified_at=datetime.fromisoformat(model["modified_at"].replace("Z", "+00:00"))
            if model.get("modified_at")
            else None,
        )
        for model in payload.get("models", [])
    ]


@router.get(
    "/models",
    response_model=AvailableModelsResponse,
    summary="List available Ollama models",
    description=(
        "Returns the local Ollama model catalog for client-side selection. "
        "This endpoint is preferred over embedding model details into the health check."
    ),
    responses={
        200: {"description": "Available local Ollama models."},
        401: {"description": "Missing or invalid authentication credentials."},
        502: {"description": "Ollama catalog unavailable."},
    },
)
def list_models(
    _profile: UserProfile = Depends(
        require_roles("viewer", "operator", "intel_user", "developer", "admin", "internal_service")
    ),
) -> AvailableModelsResponse:
    config = AppConfig.from_env()

    try:
        models = _fetch_ollama_models(config)
    except Exception as exc:
        logger.error("Failed to fetch Ollama model catalog: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ollama model catalog is unavailable. Please try again later.",
        )

    return AvailableModelsResponse(
        default_chat_model=config.chat_model,
        default_embedding_model=config.embedding_model,
        models=models,
    )


@router.post(
    "/access-requests",
    response_model=AccessRequestCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request governed access",
    description=(
        "Public onboarding endpoint for requesting governed access to Urban Lens Analytics. "
        "This endpoint records the request for review instead of issuing a privileged API key directly."
    ),
    responses={
        201: {"description": "Access request registered successfully."},
        422: {"description": "Invalid input payload."},
        502: {"description": "Backend registration service unavailable."},
    },
)
def create_access_request(body: AccessRequestCreateRequest) -> AccessRequestCreateResponse:
    config = AppConfig.from_env()
    try:
        store = MetadataStore(dsn=config.postgres_dsn)
        access_request_id = store.create_access_request(
            AccessRequestPayload(
                full_name=body.full_name,
                email=body.email,
                organization=body.organization,
                use_case=body.use_case,
                requested_plan_code="FREE",
                metadata_json={
                    "entrypoint": "public_system_route",
                    "public_signup_enabled": config.public_signup_enabled,
                },
            )
        )
        message = (
            "Solicitacao registrada. Um administrador precisa aprovar e emitir a credencial governada."
        )
        if config.public_signup_enabled:
            message += " O fluxo publico esta habilitado, mas a emissao automatica de chave permanece desabilitada."

        return AccessRequestCreateResponse(
            request_id=access_request_id,
            status="pending_review",
            recommended_plan="FREE",
            message=message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Public access request creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to register the access request. Please try again later.",
        )
