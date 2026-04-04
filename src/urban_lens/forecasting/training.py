"""Baseline ML training for crime-count forecasting."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from urban_lens.governance.contracts import MODEL_FEATURE_COLUMNS, MODEL_NAME, MODEL_TARGET


def split_training_holdout(training_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if training_frame.empty:
        raise ValueError("Training frame is empty.")

    unique_months = sorted(training_frame["reference_month"].unique())
    if len(unique_months) < 2:
        raise ValueError("At least two monthly partitions are required for a temporal holdout.")

    holdout_month = unique_months[-1]
    train_frame = training_frame[training_frame["reference_month"] != holdout_month].copy()
    holdout_frame = training_frame[training_frame["reference_month"] == holdout_month].copy()
    if train_frame.empty or holdout_frame.empty:
        raise ValueError("Temporal split produced an empty train or holdout partition.")
    return train_frame, holdout_frame


def train_forecast_model(
    training_frame: pd.DataFrame,
    tracking_uri: str,
    experiment_name: str = "urban-lens-medallion",
) -> dict[str, Any]:
    import mlflow
    import mlflow.sklearn

    train_frame, holdout_frame = split_training_holdout(training_frame)

    categorical_features = ["crime_type", "lsoa_code"]
    numeric_features = [column for column in MODEL_FEATURE_COLUMNS if column not in categorical_features]
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
            (
                "numeric",
                Pipeline(steps=[("imputer", SimpleImputer(strategy="constant", fill_value=0.0))]),
                numeric_features,
            ),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=200,
                    max_depth=12,
                    min_samples_leaf=1,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run() as run:
        pipeline.fit(train_frame[MODEL_FEATURE_COLUMNS], train_frame[MODEL_TARGET])
        predictions = pipeline.predict(holdout_frame[MODEL_FEATURE_COLUMNS])

        mae = mean_absolute_error(holdout_frame[MODEL_TARGET], predictions)
        rmse = float(np.sqrt(mean_squared_error(holdout_frame[MODEL_TARGET], predictions)))
        denominator = np.maximum(np.abs(holdout_frame[MODEL_TARGET].to_numpy()), 1.0)
        mape = float(np.mean(np.abs(holdout_frame[MODEL_TARGET].to_numpy() - predictions) / denominator))

        mlflow.log_params(
            {
                "model_name": MODEL_NAME,
                "target_name": MODEL_TARGET,
                "training_rows": len(train_frame),
                "holdout_rows": len(holdout_frame),
            }
        )
        mlflow.log_metrics({"mae": mae, "rmse": rmse, "mape": mape})
        mlflow.sklearn.log_model(sk_model=pipeline, artifact_path="model")

        training_window_start = str(train_frame["reference_month"].min())
        training_window_end = str(train_frame["reference_month"].max())
        return {
            "model_name": MODEL_NAME,
            "run_id": run.info.run_id,
            "artifact_uri": run.info.artifact_uri,
            "metrics": {"mae": float(mae), "rmse": rmse, "mape": float(mape)},
            "training_window_start": training_window_start,
            "training_window_end": training_window_end,
            "pipeline": pipeline,
        }


def score_future_period(model_pipeline: Pipeline, scoring_frame: pd.DataFrame) -> pd.DataFrame:
    if scoring_frame.empty:
        return scoring_frame.copy()

    predictions = model_pipeline.predict(scoring_frame[MODEL_FEATURE_COLUMNS])
    scored = scoring_frame.copy()
    scored["predicted_incident_count"] = np.round(predictions, 2)
    return scored
