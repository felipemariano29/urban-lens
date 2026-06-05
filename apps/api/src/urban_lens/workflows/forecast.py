"""Forecast training and publication workflow."""
from __future__ import annotations

from typing import Any

from urban_lens.core.hashing import dataframe_hash
from urban_lens.core.settings import AppConfig
from urban_lens.forecasting.training import score_future_period, train_forecast_model
from urban_lens.governance.contracts import (
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


def train_and_register_forecast_model(
    training_object_key: str,
    training_dataset_version_id: str,
    scoring_object_key: str,
    scoring_dataset_version_id: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    metadata_store: MetadataStore | None = None,
) -> dict[str, Any]:
    storage = storage or MinIOStorage(config)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

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

    training_frame = storage.read_parquet(training_object_key)
    scoring_frame = storage.read_parquet(scoring_object_key)
    model_summary = train_forecast_model(
        training_frame,
        config.mlflow_tracking_uri,
        run_params={
            "pipeline_run_id": pipeline_run_id,
            "training_dataset_version_id": training_dataset_version_id,
            "scoring_dataset_version_id": scoring_dataset_version_id,
            "training_object_key": training_object_key,
            "scoring_object_key": scoring_object_key,
        },
    )
    predictions = score_future_period(model_summary["pipeline"], scoring_frame)

    prediction_month = (
        str(scoring_frame["prediction_reference_month"].max())
        if not scoring_frame.empty
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

    candidate_model_version_ids: list[str] = []
    selected_model_version_id: str | None = None
    for candidate_run in model_summary["candidate_runs"]:
        is_selected = candidate_run["run_id"] == model_summary["run_id"]
        model_version_id = metadata_store.register_model_version(
            ModelVersionPayload(
                model_name=MODEL_NAME,
                model_version=candidate_run["run_id"],
                target_name=MODEL_TARGET,
                training_dataset_version_id=training_dataset_version_id,
                scoring_dataset_version_id=scoring_dataset_version_id,
                training_window_start=candidate_run["training_window_start"],
                training_window_end=candidate_run["training_window_end"],
                metrics_json={
                    **candidate_run["metrics"],
                    "candidate_model": candidate_run["candidate_model"],
                    "selected": is_selected,
                },
                artifact_uri=candidate_run["artifact_uri"],
                status="selected" if is_selected else "candidate",
            )
        )
        candidate_model_version_ids.append(model_version_id)
        if is_selected:
            selected_model_version_id = model_version_id

    if selected_model_version_id is None:
        raise ValueError("No selected model version was registered.")

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="model_training_finished",
            actor=actor,
            object_type="model_version",
            object_id=selected_model_version_id,
            details_json={
                "selected_candidate_model": model_summary["candidate_model"],
                "selected_metrics": model_summary["metrics"],
                "candidate_model_version_ids": candidate_model_version_ids,
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
        "model_version_id": selected_model_version_id,
        "candidate_model_version_ids": candidate_model_version_ids,
        "selected_candidate_model": model_summary["candidate_model"],
        "prediction_dataset_version_id": prediction_dataset_version_id,
        "prediction_object_key": prediction_object_key,
    }
