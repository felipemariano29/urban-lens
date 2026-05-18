from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from mlflow.client import MlflowClient

from urban_lens.api.core.auth import UserProfile, get_current_profile
from urban_lens.core.settings import AppConfig

logger = logging.getLogger(__name__)


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(
        request: Request,
        profile: UserProfile = Depends(get_current_profile),
    ) -> UserProfile:
        if profile.role not in allowed_roles:
            client_ip = request.client.host if request.client else "unknown"
            parts = client_ip.split(".")
            anon_ip = ".".join(parts[:-1] + ["xxx"]) if len(parts) == 4 else client_ip

            from urban_lens.api.middleware.correlation import get_correlation_id

            logger.warning(
                "Access denied | endpoint=%s method=%s role=%s ip=%s timestamp=%s request_id=%s",
                request.url.path,
                request.method,
                profile.role,
                anon_ip,
                datetime.now(timezone.utc).isoformat(),
                get_correlation_id(),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied: role '{profile.role}' is not authorised for this resource. "
                    f"Required: {sorted(allowed_roles)}."
                ),
            )
        return profile

    return dependency


def get_mlflow_client() -> MlflowClient:
    config = AppConfig.from_env()
    return MlflowClient(tracking_uri=config.mlflow_tracking_uri)