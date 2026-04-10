from __future__ import annotations

from fastapi import Header, HTTPException, status
from mlflow.client import MlflowClient

from urban_lens.core.settings import AppConfig

_ADMIN_PROFILE = "admin"


def require_admin(x_profile_name: str = Header(..., description="Caller profile name. Only 'admin' is authorised.")) -> str:
    if x_profile_name != _ADMIN_PROFILE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: profile '{x_profile_name}' does not have permission to query MLflow metadata. Required: 'admin'.",
        )
    return x_profile_name


def get_mlflow_client() -> MlflowClient:
    config = AppConfig.from_env()
    return MlflowClient(tracking_uri=config.mlflow_tracking_uri)