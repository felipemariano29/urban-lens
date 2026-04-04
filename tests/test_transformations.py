from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from urban_lens.forecasting.features import build_ml_datasets
from urban_lens.sources.police_uk import (
    UnsupportedDatasetKindError,
    build_gold_analytics_by_area_month,
    build_gold_analytics_by_area_month_category,
    build_gold_analytics_by_month_category,
    build_rag_evidence_records,
    classify_police_uk_csv_file,
    discover_supported_snapshot_files,
    detect_police_uk_csv_kind,
    normalize_crime_data,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_STREET_FILE = REPO_ROOT / "data" / "2026-01" / "2026-01-avon-and-somerset-street.csv"
REAL_OUTCOMES_FILE = REPO_ROOT / "data" / "2026-01" / "2026-01-avon-and-somerset-outcomes.csv"
REAL_STOP_AND_SEARCH_FILE = REPO_ROOT / "data" / "2026-01" / "2026-01-avon-and-somerset-stop-and-search.csv"


def test_normalize_crime_data_infers_reference_month_from_source_file() -> None:
    raw_frame = pd.DataFrame(
        {
            "Reported by": ["Metropolitan Police Service"],
            "Falls within": ["Metropolitan Police Service"],
            "Longitude": [-0.123],
            "Latitude": [51.501],
            "LSOA code": ["E01004736"],
            "LSOA name": ["Westminster 001A"],
            "Crime type": ["Anti-social behaviour"],
            "Last outcome category": ["Under investigation"],
            "Context": [None],
        }
    )

    normalized = normalize_crime_data(raw_frame, source_file="2024-01-metropolitan-street.csv")

    assert normalized.loc[0, "reference_month"] == "2024-01"
    assert normalized.loc[0, "crime_type"] == "anti_social_behaviour"
    assert normalized.loc[0, "last_outcome_category"] == "under_investigation"
    assert bool(normalized.loc[0, "has_outcome"]) is True


def test_real_street_csv_normalizes_to_supported_silver_schema() -> None:
    raw_frame = pd.read_csv(REAL_STREET_FILE)

    normalized = normalize_crime_data(raw_frame, source_file=str(REAL_STREET_FILE))

    assert not normalized.empty
    assert normalized["reference_month"].eq("2026-01").all()
    assert "crime_id" in normalized.columns
    assert "crime_type" in normalized.columns
    assert normalized["crime_type"].notna().all()
    assert normalized["record_hash"].is_unique


def test_non_street_csv_is_rejected() -> None:
    raw_frame = pd.read_csv(REAL_OUTCOMES_FILE)

    with pytest.raises(UnsupportedDatasetKindError):
        normalize_crime_data(raw_frame, source_file=str(REAL_OUTCOMES_FILE))


def test_can_classify_real_snapshot_files() -> None:
    assert classify_police_uk_csv_file(REAL_STREET_FILE) == "street"
    assert classify_police_uk_csv_file(REAL_OUTCOMES_FILE) == "outcomes"
    assert classify_police_uk_csv_file(REAL_STOP_AND_SEARCH_FILE) == "stop-and-search"

    supported_files, skipped_files = discover_supported_snapshot_files(REPO_ROOT / "data" / "2026-01")

    assert REAL_STREET_FILE in supported_files
    assert REAL_OUTCOMES_FILE in skipped_files
    assert REAL_STOP_AND_SEARCH_FILE in skipped_files
    assert len(supported_files) > 0


def test_gold_aggregations_produce_specific_and_aggregated_views() -> None:
    silver_frame = pd.DataFrame(
        [
            {
                "reference_month": "2024-01",
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
                "reference_month": "2024-01",
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
            {
                "reference_month": "2024-01",
                "crime_id": "crime-3",
                "reported_by": "Force A",
                "falls_within": "Force A",
                "longitude": 1.5,
                "latitude": 2.5,
                "location": None,
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "robbery",
                "last_outcome_category": None,
                "context": None,
                "has_outcome": False,
                "has_context": False,
                "source_file": "bronze/file.csv",
                "ingested_at": "2026-03-20T00:00:00+00:00",
                "record_hash": "3",
            },
        ]
    )

    area_month_category = build_gold_analytics_by_area_month_category(silver_frame)
    area_month = build_gold_analytics_by_area_month(area_month_category)
    month_category = build_gold_analytics_by_month_category(area_month_category)
    rag_records = build_rag_evidence_records(area_month, area_month_category, month_category)

    burglary = area_month_category[area_month_category["crime_type"] == "burglary"].iloc[0]
    assert burglary["incident_count"] == 2
    assert burglary["context_present_ratio"] == 0.5

    overview = area_month.iloc[0]
    assert overview["incident_count"] == 3
    assert overview["dominant_crime_type"] == "burglary"
    assert month_category.iloc[0]["crime_type"] == "burglary"
    assert not rag_records.empty


def test_ml_datasets_build_lags_and_future_target() -> None:
    analytics_frame = pd.DataFrame(
        [
            {
                "reference_month": "2024-01",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count": 10,
                "outcome_known_count": 5,
                "context_present_count": 1,
                "longitude_mean": 1.0,
                "latitude_mean": 2.0,
                "outcome_known_ratio": 0.5,
                "context_present_ratio": 0.1,
            },
            {
                "reference_month": "2024-02",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count": 12,
                "outcome_known_count": 6,
                "context_present_count": 1,
                "longitude_mean": 1.0,
                "latitude_mean": 2.0,
                "outcome_known_ratio": 0.5,
                "context_present_ratio": 0.1,
            },
            {
                "reference_month": "2024-03",
                "lsoa_code": "E1",
                "lsoa_name": "Area 1",
                "crime_type": "burglary",
                "incident_count": 9,
                "outcome_known_count": 4,
                "context_present_count": 2,
                "longitude_mean": 1.0,
                "latitude_mean": 2.0,
                "outcome_known_ratio": 0.44,
                "context_present_ratio": 0.22,
            },
        ]
    )

    training_set, scoring_set = build_ml_datasets(analytics_frame)

    assert len(training_set) == 2
    assert len(scoring_set) == 1
    assert training_set.loc[0, "incident_count_next_period"] == 12
    assert training_set.loc[1, "incident_count_lag_1"] == 10
    assert scoring_set.loc[0, "prediction_reference_month"] == "2024-04"
