"""Forecast training and publication workflow."""
from __future__ import annotations

import pandas as pd

from urban_lens.core.hashing import dataframe_hash
from urban_lens.core.settings import AppConfig
from urban_lens.forecasting.features import build_ml_datasets
from urban_lens.forecasting.training import score_future_period, train_forecast_model
from urban_lens.governance.contracts import (
    GOLD_ANALYTICS_AREA_MONTH_CATEGORY,
    GOLD_LAYER,
    GOLD_ML_PREDICTIONS,
    MODEL_NAME,
    MODEL_TARGET,
    AuditEventPayload,
    DatasetVersionPayload,
    ModelVersionPayload,
    PipelineRunPayload,
)
from urban_lens.governance.store import MetadataStore
from urban_lens.infrastructure.object_store import MinIOStorage


def _extract_year_from_object_key(object_key: str) -> str:
    marker = "year="
    start = object_key.index(marker) + len(marker)
    return object_key[start:start + 4]


def _load_historical_area_month_category(
    storage: MinIOStorage,
    year: str,
) -> pd.DataFrame:
    prefix = f"{GOLD_ANALYTICS_AREA_MONTH_CATEGORY}/year={year}/"
    paginator = storage.client.get_paginator("list_objects_v2")

    frames: list[pd.DataFrame] = []
    for page in paginator.paginate(Bucket=storage.bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                frames.append(storage.read_parquet(key))

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(
        ["reference_month", "lsoa_code", "crime_type"]
    ).reset_index(drop=True)
    return combined


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
            details_json={
                "training_object_key": training_object_key,
                "scoring_object_key": scoring_object_key,
            },
        )
    )

    year = _extract_year_from_object_key(training_object_key)

    historical_area_month_category = _load_historical_area_month_category(
        storage=storage,
        year=year,
    )

    if historical_area_month_category.empty:
        raise ValueError(
            f"No historical Gold analytics data found under year={year}."
        )

    training_frame, scoring_frame = build_ml_datasets(historical_area_month_category)

    if training_frame.empty:
        raise ValueError(
            "Combined training frame is still empty after loading historical data."
        )

    model_summary = train_forecast_model(training_frame, config.mlflow_tracking_uri)
    predictions = score_future_period(model_summary["pipeline"], scoring_frame)

    prediction_month = (
        str(predictions["prediction_reference_month"].max())
        if not predictions.empty
        else "unknown"
    )
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
            metadata_json={
                "gold_product": GOLD_ML_PREDICTIONS,
                "pipeline_run_id": pipeline_run_id,
            },
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