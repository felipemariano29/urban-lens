"""Runtime configuration for Urban-Lens jobs and services."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return [v.strip() for v in raw_value.split(",") if v.strip()]


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str
    s3_secure: bool
    postgres_dsn: str
    mlflow_tracking_uri: str
    artifact_dir: Path
    milvus_uri: str
    ollama_base_url: str
    embedding_model: str
    cors_origins: list[str]

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            s3_endpoint_url=os.getenv("URBAN_LENS_S3_ENDPOINT_URL", "http://localhost:9000"),
            s3_access_key=os.getenv("URBAN_LENS_S3_ACCESS_KEY", "minioadmin"),
            s3_secret_key=os.getenv("URBAN_LENS_S3_SECRET_KEY", "minioadmin"),
            s3_bucket=os.getenv("URBAN_LENS_S3_BUCKET", "urban-lens"),
            s3_region=os.getenv("URBAN_LENS_S3_REGION", "us-east-1"),
            s3_secure=_env_bool("URBAN_LENS_S3_SECURE", False),
            postgres_dsn=os.getenv(
                "URBAN_LENS_POSTGRES_DSN",
                "postgresql://urban_lens:urban_lens@localhost:5432/urban_lens",
            ),
            mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5005"),
            artifact_dir=Path(os.getenv("URBAN_LENS_ARTIFACT_DIR", ".artifacts")),
            milvus_uri=os.getenv("URBAN_LENS_MILVUS_URI", "http://localhost:19530"),
            ollama_base_url=os.getenv("URBAN_LENS_OLLAMA_BASE_URL", "http://localhost:11434"),
            embedding_model=os.getenv("URBAN_LENS_EMBEDDING_MODEL", "nomic-embed-text"),
            cors_origins=_env_list("URBAN_LENS_CORS_ORIGINS", ["*"]),
        )

    def s3_client_kwargs(self) -> dict[str, object]:
        return {
            "endpoint_url": self.s3_endpoint_url,
            "aws_access_key_id": self.s3_access_key,
            "aws_secret_access_key": self.s3_secret_key,
            "region_name": self.s3_region,
            "use_ssl": self.s3_secure,
        }
