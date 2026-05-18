from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from urban_lens.api.schemas import AccessCredentialRequest, AccessCredentialResponse
from urban_lens.core.settings import AppConfig
from urban_lens.governance import ApiClientPayload, ApiKeyPayload, GovernedUserPayload, MetadataStore


def issue_access_credential(body: AccessCredentialRequest) -> AccessCredentialResponse:
    config = AppConfig.from_env()
    store = MetadataStore(dsn=config.postgres_dsn)

    plan = store.get_service_plan_by_code(body.plan_code)
    if plan is None:
        raise ValueError(f"Unknown service plan code: {body.plan_code}")

    user_id = store.create_governed_user(
        GovernedUserPayload(
            full_name=body.full_name,
            email=body.email,
            organization=body.organization,
            role=body.role,
        )
    )
    client_id = store.create_api_client(
        ApiClientPayload(
            user_id=user_id,
            plan_code=plan["code"],
            client_name=body.client_name,
        )
    )

    key_prefix = secrets.token_hex(6)
    key_secret = secrets.token_urlsafe(24)
    api_key = f"ul_{key_prefix}_{key_secret}"
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    api_key_id = store.issue_api_key(
        ApiKeyPayload(
            client_id=client_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            expires_at=_normalize_expiration(body.expires_at),
            metadata_json={"issued_via": "api"},
        )
    )

    return AccessCredentialResponse(
        user_id=user_id,
        client_id=client_id,
        api_key_id=api_key_id,
        role=body.role,
        plan_code=plan["code"],
        client_name=body.client_name,
        key_prefix=key_prefix,
        api_key=api_key,
        expires_at=body.expires_at,
    )


def _normalize_expiration(expires_at: datetime | None) -> datetime | None:
    if expires_at is None:
        return None
    return expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=UTC)
