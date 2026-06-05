"""Bronze ingestion workflow."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from urban_lens.core.hashing import sha256_file
from urban_lens.core.settings import AppConfig
from urban_lens.governance.contracts import (
    BRONZE_LAYER,
    AuditEventPayload,
    DatasetVersionPayload,
    PipelineRunPayload,
)
from urban_lens.governance.store import MetadataStore
from urban_lens.infrastructure.object_store import MinIOStorage
from urban_lens.sources.police_uk import infer_reference_month, validate_supported_dataset_kind


def ingest_to_bronze(
    csv_path: Path,
    source_name: str,
    force_name: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    metadata_store: MetadataStore | None = None,
) -> dict[str, str]:
    storage = storage or MinIOStorage(config)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    raw_frame = pd.read_csv(csv_path)
    explicit_month = raw_frame["Month"].iloc[0] if "Month" in raw_frame.columns and not raw_frame.empty else None
    reference_month = infer_reference_month(explicit_month, csv_path.name)
    object_key = (
        f"bronze/{source_name}/crimes/year={reference_month[:4]}/month={reference_month[5:7]}"
        f"/force={force_name}/{csv_path.name}"
    )

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="ingest_manual",
            run_type="manual",
            status="running",
            triggered_by=actor,
        )
    )
    try:
        dataset_kind = validate_supported_dataset_kind(raw_frame, str(csv_path))
        metadata_store.register_audit_event(
            AuditEventPayload(
                event_type="ingest_started",
                actor=actor,
                object_type="pipeline_run",
                object_id=pipeline_run_id,
                details_json={
                    "source_path": str(csv_path),
                    "target_object": object_key,
                    "dataset_kind": dataset_kind,
                },
            )
        )

        row_count = len(raw_frame)
        content_hash = sha256_file(csv_path)
        storage.upload_file(csv_path, object_key)

        dataset_version_id = metadata_store.register_dataset_version(
            DatasetVersionPayload(
                source_name=source_name,
                layer=BRONZE_LAYER,
                logical_name="police_uk_street_crimes_raw",
                version=reference_month,
                schema_version="1.0.0",
                object_path=object_key,
                row_count=row_count,
                content_hash=content_hash,
                valid_from=reference_month,
                metadata_json={
                    "force_name": force_name,
                    "pipeline_run_id": pipeline_run_id,
                    "dataset_kind": dataset_kind,
                },
            )
        )
        metadata_store.register_audit_event(
            AuditEventPayload(
                event_type="ingest_finished",
                actor=actor,
                object_type="dataset_version",
                object_id=dataset_version_id,
                details_json={"object_key": object_key, "row_count": row_count},
            )
        )
        metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", [dataset_version_id])
        return {"pipeline_run_id": pipeline_run_id, "dataset_version_id": dataset_version_id, "object_key": object_key}
    except Exception as exc:
        metadata_store.register_audit_event(
            AuditEventPayload(
                event_type="validation_failed",
                actor=actor,
                object_type="pipeline_run",
                object_id=pipeline_run_id,
                details_json={"source_path": str(csv_path), "error": str(exc)},
            )
        )
        metadata_store.finalize_pipeline_run(pipeline_run_id, "failed", [], str(exc))
        raise
