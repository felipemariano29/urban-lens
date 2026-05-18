from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import Header, HTTPException, Request, status

_JWT_ALGORITHM = "HS256"

VALID_ROLES = frozenset({"viewer", "operator", "intel_user", "developer", "admin", "internal_service"})


@dataclass(frozen=True)
class UserProfile:
    role: str
    subject: str | None = None
    user_id: str | None = None
    client_id: str | None = None
    api_key_id: str | None = None
    plan_code: str | None = None
    plan_max_top_k: int | None = None
    allowed_models: tuple[str, ...] = ()
    auth_type: str = "jwt"


def get_current_profile(
    request: Request,
    authorization: str | None = Header(None, description="Bearer JWT token."),
    x_api_key: str | None = Header(None, alias="X-API-Key", description="Internal service API key."),
) -> UserProfile:
    jwt_secret = os.getenv("URBAN_LENS_JWT_SECRET", "dev-secret-change-in-prod")
    internal_api_key = os.getenv("URBAN_LENS_INTERNAL_API_KEY", "")

    if x_api_key is not None:
        if internal_api_key and x_api_key == internal_api_key:
            profile = UserProfile(role="internal_service", auth_type="internal_api_key")
            request.state.user_profile = profile
            return profile
        profile = _authenticate_governed_api_key(x_api_key)
        request.state.user_profile = profile
        return profile

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role")
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown role '{role}'. Valid roles: {sorted(VALID_ROLES)}.",
        )

    profile = UserProfile(role=role, subject=payload.get("sub"), auth_type="jwt")
    request.state.user_profile = profile
    return profile


def _authenticate_governed_api_key(api_key: str) -> UserProfile:
    from urban_lens.core.settings import AppConfig
    from urban_lens.governance import MetadataStore

    key_prefix = _extract_key_prefix(api_key)
    store = MetadataStore(AppConfig.from_env().postgres_dsn)
    record = store.get_api_key_record(key_prefix)
    if record is None:
        raise _invalid_api_key()

    if record["api_key_status"] != "active":
        raise _invalid_api_key()
    if record["client_status"] != "active":
        raise _invalid_api_key()
    if record["user_status"] != "active":
        raise _invalid_api_key()

    expires_at = record.get("expires_at")
    if expires_at is not None and expires_at <= datetime.now(UTC):
        raise _invalid_api_key(detail="API key has expired.")

    expected_hash = str(record["key_hash"])
    computed_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(expected_hash, computed_hash):
        raise _invalid_api_key()

    store.touch_api_key_usage(record["api_key_id"], record["client_id"])
    role = str(record["role"])
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown role '{role}'. Valid roles: {sorted(VALID_ROLES)}.",
        )

    return UserProfile(
        role=role,
        subject=record.get("email"),
        user_id=record["user_id"],
        client_id=record["client_id"],
        api_key_id=record["api_key_id"],
        plan_code=record.get("plan_code"),
        plan_max_top_k=record.get("plan_max_top_k"),
        allowed_models=tuple(record.get("allowed_models") or ()),
        auth_type="governed_api_key",
    )


def _extract_key_prefix(api_key: str) -> str:
    parts = api_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "ul" or not parts[1] or not parts[2]:
        raise _invalid_api_key()
    return parts[1]


def _invalid_api_key(detail: str = "Invalid API key.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )
