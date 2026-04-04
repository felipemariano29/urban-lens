from __future__ import annotations

import sys
import types

import pandas as pd

from urban_lens.forecasting.training import train_forecast_model


def test_train_forecast_model_logs_metrics_and_returns_pipeline(monkeypatch) -> None:
    logged: dict[str, object] = {}

    mlflow_module = types.ModuleType("mlflow")
    mlflow_sklearn_module = types.ModuleType("mlflow.sklearn")

    class DummyRun:
        info = types.SimpleNamespace(run_id="run-123", artifact_uri="file:///tmp/mlruns/run-123")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def set_tracking_uri(uri: str) -> None:
        logged["tracking_uri"] = uri

    def set_experiment(name: str) -> None:
        logged["experiment_name"] = name

    def start_run() -> DummyRun:
        return DummyRun()

    def log_params(params: dict[str, object]) -> None:
        logged["params"] = params

    def log_metrics(metrics: dict[str, float]) -> None:
        logged["metrics"] = metrics

    def log_model(*, sk_model, artifact_path: str) -> None:
        logged["artifact_path"] = artifact_path
        logged["pipeline_type"] = type(sk_model).__name__

    mlflow_module.set_tracking_uri = set_tracking_uri
    mlflow_module.set_experiment = set_experiment
    mlflow_module.start_run = start_run
    mlflow_module.log_params = log_params
    mlflow_module.log_metrics = log_metrics
    mlflow_module.sklearn = mlflow_sklearn_module
    mlflow_sklearn_module.log_model = log_model

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
                "incident_count_lag_3": 0,
                "moving_avg_3": 0,
                "month_number": 1,
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
                "incident_count_lag_3": 0,
                "moving_avg_3": 10,
                "month_number": 2,
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
                "incident_count_lag_3": 0,
                "moving_avg_3": 11,
                "month_number": 3,
                "has_previous_outcome_ratio": 0.45,
                "missing_context_ratio": 0.5,
                "incident_count_next_period": 11,
            },
        ]
    )

    result = train_forecast_model(training_frame, tracking_uri="file:///tmp/mlruns")

    assert result["run_id"] == "run-123"
    assert result["metrics"]["rmse"] >= 0.0
    assert "pipeline" in result
    assert logged["tracking_uri"] == "file:///tmp/mlruns"
    assert logged["experiment_name"] == "urban-lens-medallion"
    assert logged["artifact_path"] == "model"
