from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import cast

import pandas as pd
import pytest

from urban_lens.core.settings import AppConfig
from urban_lens.governance.contracts import (
    GOLD_ANALYTICS_AREA_MONTH_CATEGORY,
    GOLD_LAYER,
    DatasetVersionPayload,
)
from urban_lens.sources.police_uk import UnsupportedDatasetKindError
from urban_lens.workflows import (
    bronze_to_silver,
    ingest_to_bronze,
    process_snapshot_directory,
    silver_to_gold,
    train_and_register_forecast_model,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_STREET_FILE = REPO_ROOT / "data" / "2026-01" / "2026-01-avon-and-somerset-street.csv"
REAL_OUTCOMES_FILE = REPO_ROOT / "data" / "2026-01" / "2026-01-avon-and-somerset-outcomes.csv"


@dataclass
class FakeStorage:
    csv_objects: dict[str, pd.DataFrame]
    parquet_objects: dict[str, pd.DataFrame]

    def __init__(self) -> None:
        self.csv_objects = {}
        self.parquet_objects = {}

    def upload_file(self, local_path: Path, object_key: str, content_type: str = "text/csv") -> None:
        self.csv_objects[object_key] = pd.read_csv(local_path)

    def read_csv(self, object_key: str) -> pd.DataFrame:
        return self.csv_objects[object_key].copy()

    def write_parquet(self, dataframe: pd.DataFrame, object_key: str) -> None:
        self.parquet_objects[object_key] = dataframe.copy()

    def read_parquet(self, object_key: str) -> pd.DataFrame:
        return self.parquet_objects[object_key].copy()


class FakeMetadataStore:
    def __init__(self) -> None:
        self.pipeline_runs: dict[str, dict[str, object]] = {}
        self.dataset_versions: dict[str, dict[str, object]] = {}
        self.model_versions: dict[str, dict[str, object]] = {}
        self.lineage_edges: list[dict[str, object]] = []
        self.audit_events: list[dict[str, object]] = []
        self._run_counter = 0
        self._dataset_counter = 0
        self._model_counter = 0
        self._lineage_counter = 0
        self._audit_counter = 0

    def register_pipeline_run(self, payload) -> str:
        self._run_counter += 1
        run_id = f"run-{self._run_counter}"
        self.pipeline_runs[run_id] = {
            "payload": payload,
            "status": payload.status,
            "output_versions": list(payload.output_versions),
            "error_summary": payload.error_summary,
        }
        return run_id

    def finalize_pipeline_run(self, pipeline_run_id: str, status: str, output_versions: list[str], error_summary=None) -> None:
        self.pipeline_runs[pipeline_run_id]["status"] = status
        self.pipeline_runs[pipeline_run_id]["output_versions"] = list(output_versions)
        self.pipeline_runs[pipeline_run_id]["error_summary"] = error_summary

    def register_dataset_version(self, payload) -> str:
        self._dataset_counter += 1
        dataset_version_id = f"dataset-{self._dataset_counter}"
        self.dataset_versions[dataset_version_id] = {"payload": payload}
        return dataset_version_id

    def list_dataset_versions(
        self,
        *,
        logical_name: str | None = None,
        layer: str | None = None,
        version_prefix: str | None = None,
        version_lte: str | None = None,
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for dataset_version_id, record in self.dataset_versions.items():
            payload = record["payload"]
            if logical_name is not None and payload.logical_name != logical_name:
                continue
            if layer is not None and payload.layer != layer:
                continue
            if version_prefix is not None and not payload.version.startswith(version_prefix):
                continue
            if version_lte is not None and payload.version > version_lte:
                continue
            records.append(
                {
                    "id": dataset_version_id,
                    "layer": payload.layer,
                    "logical_name": payload.logical_name,
                    "version": payload.version,
                    "object_path": payload.object_path,
                }
            )
        return sorted(records, key=lambda record: (record["version"], record["object_path"]))

    def register_lineage(
        self,
        upstream_dataset_version_id: str,
        downstream_dataset_version_id: str,
        transformation_name: str,
        pipeline_run_id: str,
    ) -> str:
        self._lineage_counter += 1
        lineage_id = f"lineage-{self._lineage_counter}"
        self.lineage_edges.append(
            {
                "id": lineage_id,
                "upstream_dataset_version_id": upstream_dataset_version_id,
                "downstream_dataset_version_id": downstream_dataset_version_id,
                "transformation_name": transformation_name,
                "pipeline_run_id": pipeline_run_id,
            }
        )
        return lineage_id

    def register_audit_event(self, payload) -> str:
        self._audit_counter += 1
        event_id = f"audit-{self._audit_counter}"
        self.audit_events.append({"id": event_id, "payload": payload})
        return event_id

    def register_model_version(self, payload) -> str:
        self._model_counter += 1
        model_version_id = f"model-{self._model_counter}"
        self.model_versions[model_version_id] = {"payload": payload}
        return model_version_id


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        s3_endpoint_url="http://localhost:9000",
        s3_access_key="minioadmin",
        s3_secret_key="minioadmin",
        s3_bucket="urban-lens",
        s3_region="us-east-1",
        s3_secure=False,
        postgres_dsn="postgresql://urban_lens:urban_lens@localhost:5432/urban_lens",
        mlflow_tracking_uri="http://localhost:5000",
        artifact_dir=tmp_path,
    )


def test_ingest_to_bronze_accepts_real_street_csv(tmp_path: Path) -> None:
    storage = FakeStorage()
    metadata_store = FakeMetadataStore()

    result = ingest_to_bronze(
        csv_path=REAL_STREET_FILE,
        source_name="data.police.uk",
        force_name="avon-and-somerset",
        actor="kaique.govani",
        config=make_config(tmp_path),
        storage=storage,
        metadata_store=metadata_store,
    )

    assert result["object_key"] in storage.csv_objects
    bronze_payload = metadata_store.dataset_versions[result["dataset_version_id"]]["payload"]
    assert bronze_payload.logical_name == "police_uk_street_crimes_raw"
    assert bronze_payload.metadata_json["dataset_kind"] == "street"
    assert metadata_store.pipeline_runs[result["pipeline_run_id"]]["status"] == "completed"


def test_ingest_to_bronze_rejects_outcomes_csv(tmp_path: Path) -> None:
    storage = FakeStorage()
    metadata_store = FakeMetadataStore()

    with pytest.raises(UnsupportedDatasetKindError):
        ingest_to_bronze(
            csv_path=REAL_OUTCOMES_FILE,
            source_name="data.police.uk",
            force_name="avon-and-somerset",
            actor="kaique.govani",
            config=make_config(tmp_path),
            storage=storage,
            metadata_store=metadata_store,
        )

    assert any(event["payload"].event_type == "validation_failed" for event in metadata_store.audit_events)
    assert any(run["status"] == "failed" for run in metadata_store.pipeline_runs.values())


def test_bronze_to_gold_pipeline_runs_end_to_end_on_real_street_csv(tmp_path: Path) -> None:
    storage = FakeStorage()
    metadata_store = FakeMetadataStore()
    config = make_config(tmp_path)

    bronze_result = ingest_to_bronze(
        csv_path=REAL_STREET_FILE,
        source_name="data.police.uk",
        force_name="avon-and-somerset",
        actor="kaique.govani",
        config=config,
        storage=storage,
        metadata_store=metadata_store,
    )
    silver_result = bronze_to_silver(
        bronze_object_key=bronze_result["object_key"],
        bronze_dataset_version_id=bronze_result["dataset_version_id"],
        actor="kaique.govani",
        config=config,
        storage=storage,
        metadata_store=metadata_store,
    )
    gold_result = silver_to_gold(
        silver_object_key=silver_result["object_key"],
        silver_dataset_version_id=silver_result["dataset_version_id"],
        actor="kaique.govani",
        config=config,
        storage=storage,
        metadata_store=metadata_store,
    )

    silver_frame = storage.parquet_objects[silver_result["object_key"]]
    assert "crime_id" in silver_frame.columns
    assert silver_frame["reference_month"].eq("2026-01").all()

    gold_keys = {
        gold_result["crime_metrics_area_month_category_object_key"],
        gold_result["crime_metrics_area_month_object_key"],
        gold_result["crime_metrics_month_category_object_key"],
        gold_result["crime_chunks_object_key"],
        gold_result["forecast_training_set_object_key"],
        gold_result["forecast_scoring_set_object_key"],
    }
    assert gold_keys.issubset(storage.parquet_objects.keys())
    assert len(metadata_store.lineage_edges) >= 1


def test_process_snapshot_directory_consolidates_supported_files(tmp_path: Path) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    shutil.copy2(REAL_STREET_FILE, snapshot_dir / REAL_STREET_FILE.name)
    shutil.copy2(REAL_OUTCOMES_FILE, snapshot_dir / REAL_OUTCOMES_FILE.name)

    storage = FakeStorage()
    metadata_store = FakeMetadataStore()
    result = process_snapshot_directory(
        snapshot_dir=snapshot_dir,
        source_name="data.police.uk",
        actor="kaique.govani",
        config=make_config(tmp_path),
        storage=storage,
        metadata_store=metadata_store,
    )

    assert result["supported_file_count"] == 1
    assert result["skipped_file_count"] == 1
    assert result["silver_object_key"] in storage.parquet_objects
    assert result["gold"]["crime_metrics_area_month_category_object_key"] in storage.parquet_objects
    assert len(result["bronze_dataset_version_ids"]) == 1


def test_silver_to_gold_builds_cumulative_ml_datasets_from_historical_gold_analytics(tmp_path: Path) -> None:
    storage = FakeStorage()
    metadata_store = FakeMetadataStore()
    config = make_config(tmp_path)

    historical_key = "gold/analytics/crime_metrics_area_month_category/year=2024/month=01/part-000.parquet"
    historical_frame = pd.DataFrame(
        [
            {
                "reference_month": "2024-01",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count": 3,
                "outcome_known_ratio": 0.5,
                "context_present_ratio": 0.25,
            }
        ]
    )
    storage.write_parquet(historical_frame, historical_key)
    historical_dataset_version_id = metadata_store.register_dataset_version(
        DatasetVersionPayload(
            source_name="data.police.uk",
            layer=GOLD_LAYER,
            logical_name="crime_metrics_area_month_category",
            version="2024-01",
            schema_version="1.0.0",
            object_path=historical_key,
            row_count=len(historical_frame),
            content_hash="hash-2024-01",
            valid_from="2024-01",
            metadata_json={"gold_product": GOLD_ANALYTICS_AREA_MONTH_CATEGORY},
        )
    )

    silver_key = "silver/police_uk/crimes_standardized/year=2024/month=02/part-000.parquet"
    silver_frame = pd.DataFrame(
        [
            {
                "reference_month": "2024-02",
                "crime_id": "crime-1",
                "reported_by": "Force A",
                "falls_within": "Force A",
                "longitude": 1.0,
                "latitude": 2.0,
                "location": None,
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "last_outcome_category": "investigating",
                "context": None,
                "has_outcome": True,
                "has_context": False,
                "source_file": "bronze/file.csv",
                "ingested_at": "2026-03-20T00:00:00+00:00",
                "record_hash": "1",
            },
            {
                "reference_month": "2024-02",
                "crime_id": "crime-2",
                "reported_by": "Force A",
                "falls_within": "Force A",
                "longitude": 1.0,
                "latitude": 2.0,
                "location": None,
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "last_outcome_category": "investigating",
                "context": "context",
                "has_outcome": True,
                "has_context": True,
                "source_file": "bronze/file.csv",
                "ingested_at": "2026-03-20T00:00:00+00:00",
                "record_hash": "2",
            },
        ]
    )
    storage.write_parquet(silver_frame, silver_key)

    result = silver_to_gold(
        silver_object_key=silver_key,
        silver_dataset_version_id="silver-2024-02",
        actor="kaique.govani",
        config=config,
        storage=storage,
        metadata_store=metadata_store,
    )

    training_set = storage.parquet_objects[result["forecast_training_set_object_key"]]
    scoring_set = storage.parquet_objects[result["forecast_scoring_set_object_key"]]

    assert training_set["reference_month"].tolist() == ["2024-01"]
    assert training_set["incident_count_next_period"].tolist() == [2.0]
    assert scoring_set["reference_month"].tolist() == ["2024-02"]
    assert scoring_set["prediction_reference_month"].tolist() == ["2024-03"]

    expected_upstream_ids = {
        historical_dataset_version_id,
        result["crime_metrics_area_month_category_dataset_version_id"],
    }
    training_lineage = {
        edge["upstream_dataset_version_id"]
        for edge in metadata_store.lineage_edges
        if edge["downstream_dataset_version_id"] == result["forecast_training_set_dataset_version_id"]
    }
    scoring_lineage = {
        edge["upstream_dataset_version_id"]
        for edge in metadata_store.lineage_edges
        if edge["downstream_dataset_version_id"] == result["forecast_scoring_set_dataset_version_id"]
    }

    assert expected_upstream_ids.issubset(training_lineage)
    assert expected_upstream_ids.issubset(scoring_lineage)


def test_train_and_register_forecast_model_uses_published_gold_ml_datasets_and_registers_all_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import urban_lens.workflows.forecast as forecast_workflow

    storage = FakeStorage()
    metadata_store = FakeMetadataStore()
    config = make_config(tmp_path)
    captured: dict[str, object] = {}

    training_key = "gold/ml/forecast_training_set/year=2024/month=04/part-000.parquet"
    scoring_key = "gold/ml/forecast_scoring_set/year=2024/month=04/part-000.parquet"
    training_frame = pd.DataFrame(
        [
            {
                "reference_month": "2024-01",
                "prediction_reference_month": "2024-02",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count_current_period": 10,
                "incident_count_lag_1": 0.0,
                "incident_count_lag_2": 0.0,
                "incident_count_lag_3": 0.0,
                "moving_avg_3": 0.0,
                "moving_avg_6": 0.0,
                "trend_lag1_vs_lag3": 0.0,
                "month_number": 1,
                "quarter": 1,
                "has_previous_outcome_ratio": 0.4,
                "missing_context_ratio": 0.7,
                "incident_count_next_period": 12.0,
            },
            {
                "reference_month": "2024-04",
                "prediction_reference_month": "2024-05",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count_current_period": 11,
                "incident_count_lag_1": 9.0,
                "incident_count_lag_2": 12.0,
                "incident_count_lag_3": 10.0,
                "moving_avg_3": 10.33,
                "moving_avg_6": 10.33,
                "trend_lag1_vs_lag3": -1.0,
                "month_number": 4,
                "quarter": 2,
                "has_previous_outcome_ratio": 0.5,
                "missing_context_ratio": 0.4,
                "incident_count_next_period": 8.0,
            },
        ]
    )
    scoring_frame = training_frame[training_frame["reference_month"] == "2024-04"].drop(
        columns=["incident_count_next_period"]
    ).reset_index(drop=True)
    storage.write_parquet(training_frame, training_key)
    storage.write_parquet(scoring_frame, scoring_key)

    def fake_train(
        training_frame_arg: pd.DataFrame,
        tracking_uri: str,
        run_params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        captured["training_frame"] = training_frame_arg.copy()
        captured["tracking_uri"] = tracking_uri
        captured["run_params"] = run_params
        return {
            "run_id": "run-random-forest",
            "candidate_model": "random_forest",
            "artifact_uri": "s3://urban-lens/mlflow/run-random-forest/artifacts",
            "metrics": {"mae": 1.0, "rmse": 1.2, "mape": 0.1},
            "training_window_start": "2024-01",
            "training_window_end": "2024-04",
            "pipeline": "best-pipeline",
            "candidate_runs": [
                {
                    "run_id": "run-ridge",
                    "candidate_model": "ridge",
                    "artifact_uri": "s3://urban-lens/mlflow/run-ridge/artifacts",
                    "metrics": {"mae": 1.3, "rmse": 1.5, "mape": 0.2},
                    "training_window_start": "2024-01",
                    "training_window_end": "2024-04",
                },
                {
                    "run_id": "run-random-forest",
                    "candidate_model": "random_forest",
                    "artifact_uri": "s3://urban-lens/mlflow/run-random-forest/artifacts",
                    "metrics": {"mae": 1.0, "rmse": 1.2, "mape": 0.1},
                    "training_window_start": "2024-01",
                    "training_window_end": "2024-04",
                },
                {
                    "run_id": "run-extra-trees",
                    "candidate_model": "extra_trees",
                    "artifact_uri": "s3://urban-lens/mlflow/run-extra-trees/artifacts",
                    "metrics": {"mae": 1.1, "rmse": 1.3, "mape": 0.12},
                    "training_window_start": "2024-01",
                    "training_window_end": "2024-04",
                },
            ],
        }

    def fake_score(model_pipeline: object, scoring_frame_arg: pd.DataFrame) -> pd.DataFrame:
        captured["model_pipeline"] = model_pipeline
        captured["scoring_frame"] = scoring_frame_arg.copy()
        scored = scoring_frame_arg.copy()
        scored["predicted_incident_count"] = [8.5]
        return scored

    monkeypatch.setattr(forecast_workflow, "train_forecast_model", fake_train)
    monkeypatch.setattr(forecast_workflow, "score_future_period", fake_score)

    result = train_and_register_forecast_model(
        training_object_key=training_key,
        training_dataset_version_id="training-apr",
        scoring_object_key=scoring_key,
        scoring_dataset_version_id="scoring-apr",
        actor="kaique.govani",
        config=config,
        storage=storage,
        metadata_store=metadata_store,
    )

    assert captured["tracking_uri"] == "http://localhost:5000"
    assert cast(pd.DataFrame, captured["training_frame"]).equals(training_frame)
    assert cast(pd.DataFrame, captured["scoring_frame"]).equals(scoring_frame)
    assert captured["run_params"] == {
        "pipeline_run_id": result["pipeline_run_id"],
        "training_dataset_version_id": "training-apr",
        "scoring_dataset_version_id": "scoring-apr",
        "training_object_key": training_key,
        "scoring_object_key": scoring_key,
    }
    assert captured["model_pipeline"] == "best-pipeline"
    assert result["prediction_object_key"] == "gold/ml/forecast_predictions/prediction_month=2024-05/part-000.parquet"
    assert result["selected_candidate_model"] == "random_forest"
    assert len(result["candidate_model_version_ids"]) == 3

    model_payloads = [record["payload"] for record in metadata_store.model_versions.values()]
    assert sum(payload.status == "selected" for payload in model_payloads) == 1
    assert {payload.metrics_json["candidate_model"] for payload in model_payloads} == {
        "ridge",
        "random_forest",
        "extra_trees",
    }
