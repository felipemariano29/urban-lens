"""Feature engineering for forecast training and scoring datasets."""
from __future__ import annotations

import pandas as pd


def build_ml_datasets(area_month_category_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = area_month_category_frame.copy()
    frame["reference_month"] = pd.PeriodIndex(frame["reference_month"], freq="M").to_timestamp()
    frame = frame.sort_values(["lsoa_code", "crime_type", "reference_month"]).reset_index(drop=True)

    grouped = frame.groupby(["lsoa_code", "crime_type"], sort=False)

    frame["incident_count_current_period"] = frame["incident_count"]
    frame["incident_count_lag_1"] = grouped["incident_count"].shift(1).fillna(0.0)
    frame["incident_count_lag_2"] = grouped["incident_count"].shift(2).fillna(0.0)
    frame["incident_count_lag_3"] = grouped["incident_count"].shift(3).fillna(0.0)

    frame["moving_avg_3"] = grouped["incident_count"].transform(
        lambda series: series.shift(1).rolling(window=3, min_periods=1).mean()
    ).fillna(0.0)

    frame["moving_avg_6"] = grouped["incident_count"].transform(
        lambda series: series.shift(1).rolling(window=6, min_periods=1).mean()
    ).fillna(0.0)

    frame["trend_lag1_vs_lag3"] = (
        frame["incident_count_lag_1"] - frame["incident_count_lag_3"]
    ).fillna(0.0)

    frame["month_number"] = frame["reference_month"].dt.month
    frame["quarter"] = frame["reference_month"].dt.quarter

    frame["has_previous_outcome_ratio"] = frame["outcome_known_ratio"].fillna(0.0)
    frame["missing_context_ratio"] = 1.0 - frame["context_present_ratio"].fillna(0.0)

    frame["incident_count_next_period"] = grouped["incident_count"].shift(-1)
    frame["prediction_reference_month"] = (frame["reference_month"].dt.to_period("M") + 1).astype(str)
    frame["reference_month"] = frame["reference_month"].dt.to_period("M").astype(str)

    selected_columns = [
        "reference_month",
        "prediction_reference_month",
        "lsoa_code",
        "lsoa_name",
        "crime_type",
        "incident_count_current_period",
        "incident_count_lag_1",
        "incident_count_lag_2",
        "incident_count_lag_3",
        "moving_avg_3",
        "moving_avg_6",
        "trend_lag1_vs_lag3",
        "month_number",
        "quarter",
        "has_previous_outcome_ratio",
        "missing_context_ratio",
        "incident_count_next_period",
    ]

    features = frame[selected_columns].copy()
    training_set = features[features["incident_count_next_period"].notna()].reset_index(drop=True)
    scoring_set = (
        features[features["incident_count_next_period"].isna()]
        .drop(columns=["incident_count_next_period"])
        .reset_index(drop=True)
    )
    return training_set, scoring_set