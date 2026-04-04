"""Pure medallion transformations for DATA.POLICE.UK crime data."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from urban_lens.governance.contracts import (
    CSV_COLUMN_ALIASES,
    SILVER_OUTPUT_COLUMNS,
    SUPPORTED_POLICE_UK_DATASET_KIND,
)


class UnsupportedDatasetKindError(ValueError):
    """Raised when the CSV format is not supported by the current MVP pipeline."""


def _normalize_column_name(column_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", column_name.strip().lower()).strip("_")


def _clean_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_label(value: object) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    return re.sub(r"[^a-z0-9]+", "_", cleaned.lower()).strip("_")


def detect_police_uk_csv_kind(raw_frame: pd.DataFrame, source_file: str) -> str:
    normalized_columns = {_normalize_column_name(column_name) for column_name in raw_frame.columns}
    source_name = Path(source_file).name.lower()

    if "crime_type" in normalized_columns:
        return "street"
    if "outcome_type" in normalized_columns or source_name.endswith("-outcomes.csv"):
        return "outcomes"
    if "object_of_search" in normalized_columns or source_name.endswith("-stop-and-search.csv"):
        return "stop-and-search"
    return "unknown"


def validate_supported_dataset_kind(raw_frame: pd.DataFrame, source_file: str) -> str:
    dataset_kind = detect_police_uk_csv_kind(raw_frame, source_file)
    if dataset_kind != SUPPORTED_POLICE_UK_DATASET_KIND:
        raise UnsupportedDatasetKindError(
            "Urban-Lens currently supports only DATA.POLICE.UK street crime CSV files. "
            f"Received dataset kind '{dataset_kind}' from '{source_file}'."
        )
    return dataset_kind


def classify_police_uk_csv_file(csv_path: Path) -> str:
    header_frame = pd.read_csv(csv_path, nrows=1)
    return detect_police_uk_csv_kind(header_frame, str(csv_path))


def discover_supported_snapshot_files(snapshot_dir: Path) -> tuple[list[Path], list[Path]]:
    supported_files: list[Path] = []
    skipped_files: list[Path] = []
    for csv_path in sorted(snapshot_dir.glob("*.csv")):
        dataset_kind = classify_police_uk_csv_file(csv_path)
        if dataset_kind == SUPPORTED_POLICE_UK_DATASET_KIND:
            supported_files.append(csv_path)
        else:
            skipped_files.append(csv_path)
    return supported_files, skipped_files


def infer_reference_month(explicit_month: object | None, source_file: str) -> str:
    if explicit_month is not None and not pd.isna(explicit_month):
        month_value = str(explicit_month).strip()
        if month_value:
            parsed = pd.Period(pd.to_datetime(month_value), freq="M")
            return str(parsed)

    partition_match = re.search(r"year=(20\d{2}).*month=(0[1-9]|1[0-2])", source_file)
    if partition_match:
        return f"{partition_match.group(1)}-{partition_match.group(2)}"

    file_match = re.search(r"(20\d{2})[-_](0[1-9]|1[0-2])", source_file)
    if file_match:
        return f"{file_match.group(1)}-{file_match.group(2)}"

    raise ValueError(
        "Unable to infer reference_month. Provide a Month column or a source path containing YYYY-MM."
    )


def normalize_crime_data(
    raw_frame: pd.DataFrame,
    source_file: str,
    default_reference_month: str | None = None,
    ingested_at: str | None = None,
) -> pd.DataFrame:
    renamed_columns = {
        original_name: CSV_COLUMN_ALIASES.get(_normalize_column_name(original_name), _normalize_column_name(original_name))
        for original_name in raw_frame.columns
    }
    frame = raw_frame.rename(columns=renamed_columns).copy()
    validate_supported_dataset_kind(frame, source_file)

    for optional_column in ("crime_id", "location", "month", "last_outcome_category", "context"):
        if optional_column not in frame.columns:
            frame[optional_column] = pd.NA

    required_columns = {"reported_by", "falls_within", "longitude", "latitude", "lsoa_code", "lsoa_name", "crime_type"}
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    normalized_ingested_at = ingested_at or datetime.now(timezone.utc).isoformat()

    frame["crime_id"] = frame["crime_id"].map(_clean_text)
    frame["reported_by"] = frame["reported_by"].map(_clean_text)
    frame["falls_within"] = frame["falls_within"].map(_clean_text)
    frame["location"] = frame["location"].map(_clean_text)
    frame["lsoa_code"] = frame["lsoa_code"].map(_clean_text)
    frame["lsoa_name"] = frame["lsoa_name"].map(_clean_text)
    frame["crime_type"] = frame["crime_type"].map(_normalize_label)
    frame["last_outcome_category"] = frame["last_outcome_category"].map(_normalize_label)
    frame["context"] = frame["context"].map(_clean_text)
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["reference_month"] = frame["month"].apply(
        lambda value: infer_reference_month(value if not pd.isna(value) else default_reference_month, source_file)
    )
    frame["has_outcome"] = frame["last_outcome_category"].notna()
    frame["has_context"] = frame["context"].notna()
    frame["source_file"] = source_file
    frame["ingested_at"] = normalized_ingested_at

    frame["record_hash"] = frame.apply(
        lambda row: hashlib.sha256(
            json.dumps(
                {
                    "crime_id": row["crime_id"],
                    "reference_month": row["reference_month"],
                    "reported_by": row["reported_by"],
                    "falls_within": row["falls_within"],
                    "longitude": row["longitude"],
                    "latitude": row["latitude"],
                    "lsoa_code": row["lsoa_code"],
                    "lsoa_name": row["lsoa_name"],
                    "crime_type": row["crime_type"],
                    "last_outcome_category": row["last_outcome_category"],
                    "context": row["context"],
                },
                default=str,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        axis=1,
    )

    silver_frame = frame[SILVER_OUTPUT_COLUMNS].drop_duplicates(subset=["record_hash"]).copy()
    silver_frame = silver_frame.sort_values(["reference_month", "lsoa_code", "crime_type", "record_hash"]).reset_index(
        drop=True
    )
    return silver_frame


def build_gold_analytics_by_area_month_category(silver_frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        silver_frame.groupby(["reference_month", "lsoa_code", "lsoa_name", "crime_type"], dropna=False)
        .agg(
            incident_count=("record_hash", "count"),
            outcome_known_count=("has_outcome", "sum"),
            context_present_count=("has_context", "sum"),
            longitude_mean=("longitude", "mean"),
            latitude_mean=("latitude", "mean"),
        )
        .reset_index()
    )
    grouped["outcome_known_ratio"] = grouped["outcome_known_count"] / grouped["incident_count"]
    grouped["context_present_ratio"] = grouped["context_present_count"] / grouped["incident_count"]
    return grouped.sort_values(["reference_month", "lsoa_code", "crime_type"]).reset_index(drop=True)


def build_gold_analytics_by_area_month(area_month_category_frame: pd.DataFrame) -> pd.DataFrame:
    base = (
        area_month_category_frame.groupby(["reference_month", "lsoa_code", "lsoa_name"], dropna=False)
        .agg(
            incident_count=("incident_count", "sum"),
            crime_type_count=("crime_type", "nunique"),
            outcome_known_ratio=("outcome_known_ratio", "mean"),
            context_present_ratio=("context_present_ratio", "mean"),
        )
        .reset_index()
    )

    dominant = (
        area_month_category_frame.sort_values(
            ["reference_month", "lsoa_code", "incident_count", "crime_type"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(subset=["reference_month", "lsoa_code"], keep="first")
        .loc[:, ["reference_month", "lsoa_code", "crime_type"]]
        .rename(columns={"crime_type": "dominant_crime_type"})
    )
    merged = base.merge(dominant, on=["reference_month", "lsoa_code"], how="left")
    return merged.sort_values(["reference_month", "lsoa_code"]).reset_index(drop=True)


def build_gold_analytics_by_month_category(area_month_category_frame: pd.DataFrame) -> pd.DataFrame:
    aggregated = (
        area_month_category_frame.groupby(["reference_month", "crime_type"], dropna=False)
        .agg(incident_count=("incident_count", "sum"))
        .reset_index()
    )
    return aggregated.sort_values(["reference_month", "incident_count", "crime_type"], ascending=[True, False, True])


def build_rag_evidence_records(
    area_month_frame: pd.DataFrame,
    area_month_category_frame: pd.DataFrame,
    month_category_frame: pd.DataFrame,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for row in area_month_category_frame.itertuples(index=False):
        title = f"{row.reference_month} {row.lsoa_name} {row.crime_type}"
        content = (
            f"In {row.reference_month}, area {row.lsoa_name} ({row.lsoa_code}) recorded "
            f"{row.incident_count} incidents for crime type {row.crime_type}. "
            f"Outcome-known ratio was {row.outcome_known_ratio:.2f} and "
            f"context-present ratio was {row.context_present_ratio:.2f}."
        )
        records.append(
            {
                "chunk_id": hashlib.sha256(f"area-month-category:{title}".encode("utf-8")).hexdigest(),
                "chunk_type": "area_month_category",
                "reference_month": row.reference_month,
                "lsoa_code": row.lsoa_code,
                "crime_type": row.crime_type,
                "title": title,
                "content": content,
            }
        )

    for row in area_month_frame.itertuples(index=False):
        title = f"{row.reference_month} {row.lsoa_name} overview"
        content = (
            f"In {row.reference_month}, area {row.lsoa_name} ({row.lsoa_code}) recorded "
            f"{row.incident_count} incidents across {row.crime_type_count} crime types. "
            f"The dominant crime type was {row.dominant_crime_type}."
        )
        records.append(
            {
                "chunk_id": hashlib.sha256(f"area-month:{title}".encode("utf-8")).hexdigest(),
                "chunk_type": "area_month",
                "reference_month": row.reference_month,
                "lsoa_code": row.lsoa_code,
                "crime_type": row.dominant_crime_type,
                "title": title,
                "content": content,
            }
        )

    for row in month_category_frame.itertuples(index=False):
        title = f"{row.reference_month} citywide {row.crime_type}"
        content = (
            f"In {row.reference_month}, crime type {row.crime_type} recorded "
            f"{row.incident_count} incidents across the available dataset."
        )
        records.append(
            {
                "chunk_id": hashlib.sha256(f"month-category:{title}".encode("utf-8")).hexdigest(),
                "chunk_type": "month_category",
                "reference_month": row.reference_month,
                "lsoa_code": None,
                "crime_type": row.crime_type,
                "title": title,
                "content": content,
            }
        )

    return pd.DataFrame.from_records(records).sort_values(["reference_month", "chunk_type", "title"]).reset_index(
        drop=True
    )
