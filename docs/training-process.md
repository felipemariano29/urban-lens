# Urban-Lens Training Process

## Overview

Urban-Lens trains a supervised regression model to forecast crime incident counts for the next calendar month. The model is named crime_count_forecaster and targets the field incident_count_next_period. Training uses only Gold ML datasets published by the medallion pipeline, is tracked in MLflow, and results in a registered model_version in PostgreSQL. The pipeline is designed to be re-run monthly when new Gold ML data is available.

## Training inputs

The training job requires two MinIO artifacts published by the silver-to-gold step. forecast_training_set is a Parquet file at `gold/ml/forecast_training_set/year=YYYY/month=MM/part-000.parquet` containing historical rows with all engineered features and the regression target. forecast_scoring_set is a Parquet file at `gold/ml/forecast_scoring_set/year=YYYY/month=MM/part-000.parquet` containing the same feature columns but without the target, used for generating predictions for the next future period. Both artifacts have a registered dataset_version in PostgreSQL which is required by the CLI.

## Feature contract

The following features are used for training and inference. Lag features: incident_count_lag_1, incident_count_lag_2, incident_count_lag_3 (previous 1, 2, 3 months). Moving averages: moving_avg_3, moving_avg_6. Trend: trend_lag1_vs_lag3 (lag_1 minus lag_3). Current period: incident_count_current_period. Seasonality: month_number (1-12), quarter (1-4). Quality ratios: has_previous_outcome_ratio, missing_context_ratio. Categorical: crime_type (normalized snake_case), lsoa_code. The target column is incident_count_next_period.

## Model candidates

Three regression algorithms are evaluated in every training run. Ridge regression serves as the linear baseline; it is fast, interpretable, and establishes a floor. RandomForestRegressor captures non-linear interactions between lag features and geographic categories. ExtraTreesRegressor provides additional variance reduction compared to random forest at the cost of slightly higher bias. All three candidates are fitted with the same preprocessing pipeline (SimpleImputer for numerics, OneHotEncoder for categoricals) and evaluated on the same temporal holdout before selection.

## Temporal split strategy

The dataset is partitioned by reference_month and split temporally, never randomly. The most recent reference_month value is held out for evaluation. All earlier months are used for training. This preserves the temporal ordering of crime data and prevents data leakage from future observations into the training window. Random cross-validation is explicitly forbidden because it would expose future monthly patterns to training folds.

## MLflow experiment tracking

Every candidate model is logged as a separate MLflow run under the experiment `urban-lens-medallion`. Logged parameters include model_class, alpha (for Ridge), n_estimators, and max_features. Logged metrics include mae, rmse, and mape computed on the temporal holdout. The best model artifact is serialized with `joblib` and logged as an MLflow artifact (`model/model.joblib`) via `mlflow.log_artifact`. This avoids a dependency on `lzma` which is not available in all Python build environments. MLflow UI is available at the MLFLOW_TRACKING_URI endpoint configured in the environment.

## Evaluation metrics and acceptance criteria

The three metrics logged for every run are: MAE (Mean Absolute Error) measuring average absolute deviation in incident count, RMSE (Root Mean Square Error) penalizing larger errors more heavily, and MAPE (Mean Absolute Percentage Error) normalizing error by the actual incident count. The best model is selected by lowest MAE on the holdout. No fixed acceptance threshold is enforced at the MVP stage; the metrics serve as baselines for future improvement. A model_version record in PostgreSQL preserves the metrics_json for disclosure in predictive API responses.

## Output artifacts

A successful training run produces three outputs. The MLflow run stores the model artifact, parameters, and metrics in the MLflow backend. The model_versions table in PostgreSQL stores model_name, model_version, target_name, training_dataset_version_id, scoring_dataset_version_id, training_window_start, training_window_end, metrics_json, and artifact_uri. The forecast_predictions Parquet file at `gold/ml/forecast_predictions/prediction_month=YYYY-MM/part-000.parquet` contains the scored output for the future period. All three are linked by the pipeline_run_id registered at job start.

## How to run the training pipeline

Run with automatic dataset resolution: `make train-latest` discovers the most recent forecast_training_set and forecast_scoring_set versions and passes them automatically. Run with explicit dataset IDs: `make train-forecast TRAINING_OBJECT_KEY=... TRAINING_DATASET_VERSION_ID=... SCORING_OBJECT_KEY=... SCORING_DATASET_VERSION_ID=...`. Required services: PostgreSQL, MinIO, MLflow. The job will fail if those services are unavailable or if no Gold ML datasets exist for the target version.

## Re-training triggers

A new training run should be initiated when new Gold ML datasets are published (typically after each monthly snapshot is processed), when model performance degrades below an acceptable threshold, or when the feature contract is updated. Re-training is safe to run multiple times for the same month because each run creates a new MLflow run and a new model_version record. Previous versions are not deleted.

## Disclosure rules for predictions

Published forecast_predictions must always be presented with the model_name, model_version, training_window_start, training_window_end, and quality metrics. Predictions must never be described as observed facts. The API response contract requires an explicit warning field in every predictive payload. Mixed responses combining historical observations and forecasts must keep the two sections logically separated.
