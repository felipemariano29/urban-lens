from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException, status

_JWT_ALGORITHM = "HS256"

VALID_ROLES = frozenset({"viewer", "operator", "intel_user", "developer", "admin", "internal_service"})


@dataclass(frozen=True)
class UserProfile:
    role: str
    subject: str | None = None


def get_current_profile(
    authorization: str | None = Header(None, description="Bearer JWT token."),
    x_api_key: str | None = Header(None, alias="X-API-Key", description="Internal service API key."),
) -> UserProfile:
    jwt_secret = os.getenv("URBAN_LENS_JWT_SECRET", "dev-secret-change-in-prod")
    internal_api_key = os.getenv("URBAN_LENS_INTERNAL_API_KEY", "")

    if x_api_key is not None:
        if not internal_api_key or x_api_key != internal_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
            )
        return UserProfile(role="internal_service")

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

    return UserProfile(role=role, subject=payload.get("sub"))
