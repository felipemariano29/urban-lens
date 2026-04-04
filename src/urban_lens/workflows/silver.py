"""Silver publication workflow."""

from __future__ import annotations

from urban_lens.core.hashing import dataframe_hash
from urban_lens.core.settings import AppConfig
from urban_lens.governance.contracts import (
    SILVER_LAYER,
    AuditEventPayload,
    DatasetVersionPayload,
    PipelineRunPayload,
)
from urban_lens.governance.store import MetadataStore
from urban_lens.infrastructure.object_store import MinIOStorage
from urban_lens.sources.police_uk import (
    detect_police_uk_csv_kind,
    normalize_crime_data,
    validate_supported_dataset_kind,
)


def bronze_to_silver(
    bronze_object_key: str,
    bronze_dataset_version_id: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    metadata_store: MetadataStore | None = None,
) -> dict[str, str]:
    storage = storage or MinIOStorage(config)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="bronze_to_silver",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[bronze_dataset_version_id],
        )
    )
    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="transform_started",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={"input_object": bronze_object_key},
        )
    )

    try:
        bronze_frame = storage.read_csv(bronze_object_key)
        dataset_kind = detect_police_uk_csv_kind(bronze_frame, bronze_object_key)
        validate_supported_dataset_kind(bronze_frame, bronze_object_key)
        silver_frame = normalize_crime_data(bronze_frame, source_file=bronze_object_key)
        reference_month = str(silver_frame["reference_month"].iloc[0])
        silver_object_key = (
            f"silver/police_uk/crimes_standardized/year={reference_month[:4]}/month={reference_month[5:7]}"
            "/part-000.parquet"
        )
        storage.write_parquet(silver_frame, silver_object_key)

        silver_dataset_version_id = metadata_store.register_dataset_version(
            DatasetVersionPayload(
                source_name="data.police.uk",
                layer=SILVER_LAYER,
                logical_name="police_uk_crimes_standardized",
                version=reference_month,
                schema_version="1.0.0",
                object_path=silver_object_key,
                row_count=len(silver_frame),
                content_hash=dataframe_hash(silver_frame),
                valid_from=reference_month,
                metadata_json={"pipeline_run_id": pipeline_run_id, "dataset_kind": dataset_kind},
            )
        )
        metadata_store.register_lineage(
            upstream_dataset_version_id=bronze_dataset_version_id,
            downstream_dataset_version_id=silver_dataset_version_id,
            transformation_name="bronze_to_silver_standardization",
            pipeline_run_id=pipeline_run_id,
        )
        metadata_store.register_audit_event(
            AuditEventPayload(
                event_type="transform_finished",
                actor=actor,
                object_type="dataset_version",
                object_id=silver_dataset_version_id,
                details_json={"output_object": silver_object_key, "row_count": len(silver_frame)},
            )
        )
        metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", [silver_dataset_version_id])
        return {
            "pipeline_run_id": pipeline_run_id,
            "dataset_version_id": silver_dataset_version_id,
            "object_key": silver_object_key,
        }
    except Exception as exc:
        metadata_store.register_audit_event(
            AuditEventPayload(
                event_type="validation_failed",
                actor=actor,
                object_type="pipeline_run",
                object_id=pipeline_run_id,
                details_json={"input_object": bronze_object_key, "error": str(exc)},
            )
        )
        metadata_store.finalize_pipeline_run(pipeline_run_id, "failed", [], str(exc))
        raise
