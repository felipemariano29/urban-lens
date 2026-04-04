"""Snapshot processing workflow."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

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
from urban_lens.sources.police_uk import discover_supported_snapshot_files, normalize_crime_data
from urban_lens.workflows.gold import silver_to_gold
from urban_lens.workflows.ingestion import ingest_to_bronze


def _derive_force_name(csv_path: Path) -> str:
    match = re.match(r"^\d{4}-\d{2}-(.+)-street$", csv_path.stem)
    if not match:
        raise ValueError(f"Unable to derive force name from snapshot filename: {csv_path.name}")
    return match.group(1)


def process_snapshot_directory(
    snapshot_dir: Path,
    source_name: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    metadata_store: MetadataStore | None = None,
) -> dict[str, object]:
    storage = storage or MinIOStorage(config)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    supported_files, skipped_files = discover_supported_snapshot_files(snapshot_dir)
    if not supported_files:
        raise ValueError(f"No supported street CSV files found in snapshot directory: {snapshot_dir}")

    bronze_results: list[dict[str, str]] = []
    silver_frames: list[pd.DataFrame] = []
    reference_months: set[str] = set()

    for csv_path in supported_files:
        bronze_result = ingest_to_bronze(
            csv_path=csv_path,
            source_name=source_name,
            force_name=_derive_force_name(csv_path),
            actor=actor,
            config=config,
            storage=storage,
            metadata_store=metadata_store,
        )
        bronze_results.append(bronze_result)
        bronze_frame = storage.read_csv(bronze_result["object_key"])
        silver_piece = normalize_crime_data(bronze_frame, source_file=bronze_result["object_key"])
        silver_frames.append(silver_piece)
        reference_months.update(silver_piece["reference_month"].unique())

    if len(reference_months) != 1:
        raise ValueError(f"Snapshot directory contains multiple reference months: {sorted(reference_months)}")

    reference_month = next(iter(reference_months))
    consolidated_silver = (
        pd.concat(silver_frames, ignore_index=True)
        .drop_duplicates(subset=["record_hash"])
        .sort_values(["reference_month", "lsoa_code", "crime_type", "record_hash"])
        .reset_index(drop=True)
    )
    silver_object_key = (
        f"silver/police_uk/crimes_standardized/year={reference_month[:4]}/month={reference_month[5:7]}"
        "/snapshot.parquet"
    )

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="snapshot_to_silver",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[result["dataset_version_id"] for result in bronze_results],
        )
    )
    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="transform_started",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={
                "snapshot_dir": str(snapshot_dir),
                "supported_file_count": len(supported_files),
                "skipped_file_count": len(skipped_files),
            },
        )
    )

    storage.write_parquet(consolidated_silver, silver_object_key)
    silver_dataset_version_id = metadata_store.register_dataset_version(
        DatasetVersionPayload(
            source_name=source_name,
            layer=SILVER_LAYER,
            logical_name="police_uk_crimes_standardized_snapshot",
            version=reference_month,
            schema_version="1.0.0",
            object_path=silver_object_key,
            row_count=len(consolidated_silver),
            content_hash=dataframe_hash(consolidated_silver),
            valid_from=reference_month,
            metadata_json={
                "pipeline_run_id": pipeline_run_id,
                "snapshot_dir": str(snapshot_dir),
                "supported_file_count": len(supported_files),
                "skipped_file_count": len(skipped_files),
            },
        )
    )

    for bronze_result in bronze_results:
        metadata_store.register_lineage(
            upstream_dataset_version_id=bronze_result["dataset_version_id"],
            downstream_dataset_version_id=silver_dataset_version_id,
            transformation_name="snapshot_bronze_to_silver_standardization",
            pipeline_run_id=pipeline_run_id,
        )

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="transform_finished",
            actor=actor,
            object_type="dataset_version",
            object_id=silver_dataset_version_id,
            details_json={
                "output_object": silver_object_key,
                "row_count": len(consolidated_silver),
                "supported_file_count": len(supported_files),
                "skipped_file_count": len(skipped_files),
            },
        )
    )
    metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", [silver_dataset_version_id])

    gold_result = silver_to_gold(
        silver_object_key=silver_object_key,
        silver_dataset_version_id=silver_dataset_version_id,
        actor=actor,
        config=config,
        storage=storage,
        metadata_store=metadata_store,
    )
    return {
        "reference_month": reference_month,
        "supported_file_count": len(supported_files),
        "skipped_file_count": len(skipped_files),
        "bronze_dataset_version_ids": [result["dataset_version_id"] for result in bronze_results],
        "silver_dataset_version_id": silver_dataset_version_id,
        "silver_object_key": silver_object_key,
        "gold": gold_result,
    }
