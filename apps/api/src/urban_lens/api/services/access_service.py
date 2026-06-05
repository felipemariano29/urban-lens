from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

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


def list_api_clients(
    *,
    user_id: str | None = None,
    include_inactive: bool = False,
) -> ApiClientListResponse:
    """List API clients with optional filtering by user."""
    config = AppConfig.from_env()
    store = MetadataStore(dsn=config.postgres_dsn)

    clients = store.list_api_clients(user_id=user_id, include_inactive=include_inactive)
    return ApiClientListResponse(clients=clients, total=len(clients))


def list_api_keys(
    *,
    client_id: str | None = None,
    include_revoked: bool = False,
) -> ApiKeyListResponse:
    """List API keys with optional filtering by client."""
    config = AppConfig.from_env()
    store = MetadataStore(dsn=config.postgres_dsn)

    keys = store.list_api_keys(client_id=client_id, include_revoked=include_revoked)
    return ApiKeyListResponse(keys=keys, total=len(keys))


def revoke_api_key(
    api_key_id: str,
    body: ApiKeyRevokeRequest | None = None,
) -> ApiKeyRevokeResponse:
    """Revoke an API key permanently."""
    config = AppConfig.from_env()
    store = MetadataStore(dsn=config.postgres_dsn)

    # Verify the key exists and get its details
    key_record = store.get_api_key_by_id(api_key_id)
    if key_record is None:
        raise ValueError(f"API key not found: {api_key_id}")

    if key_record["status"] == "revoked":
        raise ValueError(f"API key already revoked: {api_key_id}")

    reason = body.reason if body else None
    success = store.revoke_api_key(api_key_id, reason=reason)
    if not success:
        raise ValueError(f"Failed to revoke API key: {api_key_id}")

    return ApiKeyRevokeResponse(
        api_key_id=api_key_id,
        key_prefix=key_record["key_prefix"],
        status="revoked",
        revoked_at=datetime.now(UTC),
        message=f"API key {key_record['key_prefix']} has been revoked.",
    )


def rotate_api_key(
    api_key_id: str,
    body: ApiKeyRotateRequest | None = None,
) -> ApiKeyRotateResponse:
    """Rotate an API key by revoking the old one and issuing a new one."""
    config = AppConfig.from_env()
    store = MetadataStore(dsn=config.postgres_dsn)

    # Verify the key exists and get its details
    key_record = store.get_api_key_by_id(api_key_id)
    if key_record is None:
        raise ValueError(f"API key not found: {api_key_id}")

    if key_record["status"] != "active":
        raise ValueError(f"Cannot rotate non-active API key: {api_key_id} (status: {key_record['status']})")

    # Generate new key
    new_key_prefix = secrets.token_hex(6)
    new_key_secret = secrets.token_urlsafe(24)
    new_api_key = f"ul_{new_key_prefix}_{new_key_secret}"
    new_key_hash = hashlib.sha256(new_api_key.encode("utf-8")).hexdigest()

    expires_at = key_record.get("expires_at")
    if body and body.expires_at is not None:
        expires_at = _normalize_expiration(body.expires_at)

    new_api_key_id = store.rotate_api_key(
        api_key_id,
        new_key_prefix=new_key_prefix,
        new_key_hash=new_key_hash,
        expires_at=expires_at,
    )

    if new_api_key_id is None:
        raise ValueError(f"Failed to rotate API key: {api_key_id}")

    return ApiKeyRotateResponse(
        old_api_key_id=api_key_id,
        new_api_key_id=new_api_key_id,
        client_id=key_record["client_id"],
        key_prefix=new_key_prefix,
        api_key=new_api_key,
        expires_at=expires_at,
        message=f"API key rotated. Old key {key_record['key_prefix']} revoked, new key {new_key_prefix} issued.",
    )
