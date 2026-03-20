"""S3-compatible storage helpers for MinIO-backed medallion layers."""

from __future__ import annotations

import io
import json
from pathlib import Path

import boto3
import pandas as pd

from urban_lens.config import AppConfig


class MinIOStorage:
    def __init__(self, config: AppConfig) -> None:
        self.bucket = config.s3_bucket
        self.client = boto3.client("s3", **config.s3_client_kwargs())

    def upload_file(self, local_path: Path, object_key: str, content_type: str = "text/csv") -> None:
        self.client.upload_file(
            str(local_path),
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def read_csv(self, object_key: str) -> pd.DataFrame:
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return pd.read_csv(response["Body"])

    def write_parquet(self, dataframe: pd.DataFrame, object_key: str) -> None:
        buffer = io.BytesIO()
        dataframe.to_parquet(buffer, index=False)
        buffer.seek(0)
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=buffer.getvalue(),
            ContentType="application/octet-stream",
        )

    def read_parquet(self, object_key: str) -> pd.DataFrame:
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        buffer = io.BytesIO(response["Body"].read())
        buffer.seek(0)
        return pd.read_parquet(buffer)

    def write_json_records(self, records: list[dict[str, object]], object_key: str) -> None:
        payload = json.dumps(records, ensure_ascii=True, indent=2)
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )

