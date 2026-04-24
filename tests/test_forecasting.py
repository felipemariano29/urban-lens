from __future__ import annotations

import sys
import types

import pandas as pd

from urban_lens.forecasting.training import train_forecast_model


def test_train_forecast_model_logs_metrics_and_returns_pipeline(monkeypatch) -> None:
    logged: dict[str, object] = {
        "run_names": [],
        "params": [],
        "metrics": [],
        "artifact_paths": [],
    }

    mlflow_module = types.ModuleType("mlflow")
    mlflow_sklearn_module = types.ModuleType("mlflow.sklearn")
    run_ids = iter(["run-ridge", "run-random-forest", "run-extra-trees"])

    class DummyRun:
        def __init__(self, run_id: str):
            self.info = types.SimpleNamespace(
                run_id=run_id,
                artifact_uri=f"s3://urban-lens/mlflow/{run_id}/artifacts",
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def set_tracking_uri(uri: str) -> None:
        logged["tracking_uri"] = uri

    def set_experiment(name: str) -> None:
        logged["experiment_name"] = name

    def start_run(*, run_name: str | None = None) -> DummyRun:
        logged["run_names"].append(run_name)
        return DummyRun(next(run_ids))

    def log_params(params: dict[str, object]) -> None:
        logged["params"].append(params)

    def log_metrics(metrics: dict[str, float]) -> None:
        logged["metrics"].append(metrics)

    def log_artifact(local_path: str, artifact_path: str | None = None) -> None:
        logged["artifact_paths"].append(artifact_path)

    mlflow_module.set_tracking_uri = set_tracking_uri
    mlflow_module.set_experiment = set_experiment
    mlflow_module.start_run = start_run
    mlflow_module.log_params = log_params
    mlflow_module.log_metrics = log_metrics
    mlflow_module.log_artifact = log_artifact
    mlflow_module.sklearn = mlflow_sklearn_module

    monkeypatch.setitem(sys.modules, "mlflow", mlflow_module)
    monkeypatch.setitem(sys.modules, "mlflow.sklearn", mlflow_sklearn_module)

    training_frame = pd.DataFrame(
        [
            {
                "reference_month": "2024-01",
                "prediction_reference_month": "2024-02",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count_current_period": 10,
                "incident_count_lag_1": 0,
                "incident_count_lag_2": 0,
                "incident_count_lag_3": 0,
                "moving_avg_3": 0,
                "moving_avg_6": 0,
                "trend_lag1_vs_lag3": 0,
                "month_number": 1,
                "quarter": 1,
                "has_previous_outcome_ratio": 0.4,
                "missing_context_ratio": 0.7,
                "incident_count_next_period": 12,
            },
            {
                "reference_month": "2024-02",
                "prediction_reference_month": "2024-03",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count_current_period": 12,
                "incident_count_lag_1": 10,
                "incident_count_lag_2": 0,
                "incident_count_lag_3": 0,
                "moving_avg_3": 10,
                "moving_avg_6": 10,
                "trend_lag1_vs_lag3": 10,
                "month_number": 2,
                "quarter": 1,
                "has_previous_outcome_ratio": 0.5,
                "missing_context_ratio": 0.6,
                "incident_count_next_period": 9,
            },
            {
                "reference_month": "2024-03",
                "prediction_reference_month": "2024-04",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count_current_period": 9,
                "incident_count_lag_1": 12,
                "incident_count_lag_2": 10,
                "incident_count_lag_3": 0,
                "moving_avg_3": 11,
                "moving_avg_6": 11,
                "trend_lag1_vs_lag3": 12,
                "month_number": 3,
                "quarter": 1,
                "has_previous_outcome_ratio": 0.45,
                "missing_context_ratio": 0.5,
                "incident_count_next_period": 11,
            },
            {
                "reference_month": "2024-04",
                "prediction_reference_month": "2024-05",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count_current_period": 11,
                "incident_count_lag_1": 9,
                "incident_count_lag_2": 12,
                "incident_count_lag_3": 10,
                "moving_avg_3": 10.33,
                "moving_avg_6": 10.33,
                "trend_lag1_vs_lag3": -1,
                "month_number": 4,
                "quarter": 2,
                "has_previous_outcome_ratio": 0.5,
                "missing_context_ratio": 0.4,
                "incident_count_next_period": 8,
            },
        ]
    )

    result = train_forecast_model(
        training_frame,
        tracking_uri="file:///tmp/mlruns",
        run_params={
            "training_dataset_version_id": "dataset-training",
            "scoring_dataset_version_id": "dataset-scoring",
        },
    )

    assert result["run_id"] in {"run-ridge", "run-random-forest", "run-extra-trees"}
    assert result["candidate_model"] in {"ridge", "random_forest", "extra_trees"}
    assert len(result["candidate_runs"]) == 3
    assert result["metrics"]["rmse"] >= 0.0
    assert "pipeline" in result
    assert logged["tracking_uri"] == "file:///tmp/mlruns"
    assert logged["experiment_name"] == "urban-lens-medallion"
    assert logged["run_names"] == ["ridge", "random_forest", "extra_trees"]
    assert logged["artifact_paths"] == ["model", "model", "model"]
    assert {params["candidate_model"] for params in logged["params"]} == {
        "ridge",
        "random_forest",
        "extra_trees",
    }
    assert {params["training_dataset_version_id"] for params in logged["params"]} == {
        "dataset-training",
    }
    assert {params["scoring_dataset_version_id"] for params in logged["params"]} == {
        "dataset-scoring",
    }
