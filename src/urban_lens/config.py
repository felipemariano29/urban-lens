"""Runtime configuration for Urban-Lens pipeline jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str
    s3_secure: bool
    postgres_dsn: str
    mlflow_tracking_uri: str
    artifact_dir: Path

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
            mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"),
            artifact_dir=Path(os.getenv("URBAN_LENS_ARTIFACT_DIR", ".artifacts")),
        )

    def s3_client_kwargs(self) -> dict[str, object]:
        return {
            "endpoint_url": self.s3_endpoint_url,
            "aws_access_key_id": self.s3_access_key,
            "aws_secret_access_key": self.s3_secret_key,
            "region_name": self.s3_region,
            "use_ssl": self.s3_secure,
        }

