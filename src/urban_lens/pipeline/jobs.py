"""Job orchestration for Bronze, Silver, Gold, and ML pipeline stages."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from urban_lens.config import AppConfig
from urban_lens.contracts import (
    BRONZE_LAYER,
    GOLD_ANALYTICS_AREA_MONTH,
    GOLD_ANALYTICS_AREA_MONTH_CATEGORY,
    GOLD_ANALYTICS_MONTH_CATEGORY,
    GOLD_LAYER,
    GOLD_ML_PREDICTIONS,
    GOLD_ML_SCORING,
    GOLD_ML_TRAINING,
    GOLD_RAG_PRODUCT,
    MODEL_NAME,
    MODEL_TARGET,
    SILVER_LAYER,
    AuditEventPayload,
    DatasetVersionPayload,
    ModelVersionPayload,
    PipelineRunPayload,
)
from urban_lens.metadata import MetadataStore
from urban_lens.ml import score_future_period, train_forecast_model
from urban_lens.pipeline.transformations import (
    build_gold_analytics_by_area_month,
    build_gold_analytics_by_area_month_category,
    build_gold_analytics_by_month_category,
    build_ml_datasets,
    build_rag_evidence_records,
    detect_police_uk_csv_kind,
    discover_supported_snapshot_files,
    infer_reference_month,
    normalize_crime_data,
    validate_supported_dataset_kind,
)
from urban_lens.storage import MinIOStorage
from urban_lens.utils import dataframe_hash, sha256_file


def _derive_force_name(csv_path: Path) -> str:
    match = re.match(r"^\d{4}-\d{2}-(.+)-street$", csv_path.stem)
    if not match:
        raise ValueError(f"Unable to derive force name from snapshot filename: {csv_path.name}")
    return match.group(1)


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


def silver_to_gold(
    silver_object_key: str,
    silver_dataset_version_id: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    metadata_store: MetadataStore | None = None,
) -> dict[str, str]:
    storage = storage or MinIOStorage(config)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="silver_to_gold",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[silver_dataset_version_id],
        )
    )

    silver_frame = storage.read_parquet(silver_object_key)
    area_month_category = build_gold_analytics_by_area_month_category(silver_frame)
    area_month = build_gold_analytics_by_area_month(area_month_category)
    month_category = build_gold_analytics_by_month_category(area_month_category)
    rag_records = build_rag_evidence_records(area_month, area_month_category, month_category)
    training_set, scoring_set = build_ml_datasets(area_month_category)

    reference_month = str(area_month_category["reference_month"].max())
    year = reference_month[:4]
    month = reference_month[5:7]
    artifact_map = {
        GOLD_ANALYTICS_AREA_MONTH_CATEGORY: (
            area_month_category,
            f"{GOLD_ANALYTICS_AREA_MONTH_CATEGORY}/year={year}/month={month}/part-000.parquet",
            "crime_metrics_area_month_category",
        ),
        GOLD_ANALYTICS_AREA_MONTH: (
            area_month,
            f"{GOLD_ANALYTICS_AREA_MONTH}/year={year}/month={month}/part-000.parquet",
            "crime_metrics_area_month",
        ),
        GOLD_ANALYTICS_MONTH_CATEGORY: (
            month_category,
            f"{GOLD_ANALYTICS_MONTH_CATEGORY}/year={year}/month={month}/part-000.parquet",
            "crime_metrics_month_category",
        ),
        GOLD_RAG_PRODUCT: (
            rag_records,
            f"{GOLD_RAG_PRODUCT}/year={year}/month={month}/part-000.parquet",
            "crime_chunks",
        ),
        GOLD_ML_TRAINING: (
            training_set,
            f"{GOLD_ML_TRAINING}/year={year}/month={month}/part-000.parquet",
            "forecast_training_set",
        ),
        GOLD_ML_SCORING: (
            scoring_set,
            f"{GOLD_ML_SCORING}/year={year}/month={month}/part-000.parquet",
            "forecast_scoring_set",
        ),
    }

    outputs: dict[str, str] = {"pipeline_run_id": pipeline_run_id}
    output_ids: list[str] = []
    for gold_product, (frame, object_key, logical_name) in artifact_map.items():
        storage.write_parquet(frame, object_key)
        dataset_version_id = metadata_store.register_dataset_version(
            DatasetVersionPayload(
                source_name="data.police.uk",
                layer=GOLD_LAYER,
                logical_name=logical_name,
                version=reference_month,
                schema_version="1.0.0",
                object_path=object_key,
                row_count=len(frame),
                content_hash=dataframe_hash(frame),
                valid_from=reference_month,
                metadata_json={"gold_product": gold_product, "pipeline_run_id": pipeline_run_id},
            )
        )
        metadata_store.register_lineage(
            upstream_dataset_version_id=silver_dataset_version_id,
            downstream_dataset_version_id=dataset_version_id,
            transformation_name=f"silver_to_{logical_name}",
            pipeline_run_id=pipeline_run_id,
        )
        output_ids.append(dataset_version_id)
        outputs[f"{logical_name}_dataset_version_id"] = dataset_version_id
        outputs[f"{logical_name}_object_key"] = object_key

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="gold_published",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={"reference_month": reference_month, "output_count": len(output_ids)},
        )
    )
    metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", output_ids)
    return outputs


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


def train_and_register_forecast_model(
    training_object_key: str,
    training_dataset_version_id: str,
    scoring_object_key: str,
    scoring_dataset_version_id: str,
    actor: str,
    config: AppConfig,
) -> dict[str, str]:
    storage = MinIOStorage(config)
    metadata_store = MetadataStore(config.postgres_dsn)

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="train_forecast_model",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[training_dataset_version_id, scoring_dataset_version_id],
        )
    )
    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="model_training_started",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={"training_object_key": training_object_key, "scoring_object_key": scoring_object_key},
        )
    )

    training_frame = storage.read_parquet(training_object_key)
    scoring_frame = storage.read_parquet(scoring_object_key)
    model_summary = train_forecast_model(training_frame, config.mlflow_tracking_uri)
    predictions = score_future_period(model_summary["pipeline"], scoring_frame)

    prediction_month = str(predictions["prediction_reference_month"].max()) if not predictions.empty else "unknown"
    prediction_object_key = (
        f"{GOLD_ML_PREDICTIONS}/prediction_month={prediction_month}/part-000.parquet"
    )
    storage.write_parquet(predictions, prediction_object_key)
    prediction_dataset_version_id = metadata_store.register_dataset_version(
        DatasetVersionPayload(
            source_name="data.police.uk",
            layer=GOLD_LAYER,
            logical_name="forecast_predictions",
            version=prediction_month,
            schema_version="1.0.0",
            object_path=prediction_object_key,
            row_count=len(predictions),
            content_hash=dataframe_hash(predictions),
            valid_from=prediction_month,
            metadata_json={"gold_product": GOLD_ML_PREDICTIONS, "pipeline_run_id": pipeline_run_id},
        )
    )
    metadata_store.register_lineage(
        upstream_dataset_version_id=scoring_dataset_version_id,
        downstream_dataset_version_id=prediction_dataset_version_id,
        transformation_name="forecast_model_scoring",
        pipeline_run_id=pipeline_run_id,
    )

    model_version_id = metadata_store.register_model_version(
        ModelVersionPayload(
            model_name=MODEL_NAME,
            model_version=model_summary["run_id"],
            target_name=MODEL_TARGET,
            training_dataset_version_id=training_dataset_version_id,
            scoring_dataset_version_id=scoring_dataset_version_id,
            training_window_start=model_summary["training_window_start"],
            training_window_end=model_summary["training_window_end"],
            metrics_json=model_summary["metrics"],
            artifact_uri=model_summary["artifact_uri"],
        )
    )
    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="model_training_finished",
            actor=actor,
            object_type="model_version",
            object_id=model_version_id,
            details_json={
                "metrics": model_summary["metrics"],
                "prediction_dataset_version_id": prediction_dataset_version_id,
            },
        )
    )
    metadata_store.finalize_pipeline_run(
        pipeline_run_id,
        "completed",
        [prediction_dataset_version_id],
    )
    return {
        "pipeline_run_id": pipeline_run_id,
        "model_version_id": model_version_id,
        "prediction_dataset_version_id": prediction_dataset_version_id,
        "prediction_object_key": prediction_object_key,
    }
