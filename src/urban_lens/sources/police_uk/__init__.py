"""DATA.POLICE.UK source handling."""

from urban_lens.sources.police_uk.transformations import (
    UnsupportedDatasetKindError,
    build_gold_analytics_by_area_month,
    build_gold_analytics_by_area_month_category,
    build_gold_analytics_by_month_category,
    build_rag_evidence_records,
    classify_police_uk_csv_file,
    detect_police_uk_csv_kind,
    discover_supported_snapshot_files,
    infer_reference_month,
    normalize_crime_data,
    validate_supported_dataset_kind,
)

__all__ = [
    "UnsupportedDatasetKindError",
    "build_gold_analytics_by_area_month",
    "build_gold_analytics_by_area_month_category",
    "build_gold_analytics_by_month_category",
    "build_rag_evidence_records",
    "classify_police_uk_csv_file",
    "detect_police_uk_csv_kind",
    "discover_supported_snapshot_files",
    "infer_reference_month",
    "normalize_crime_data",
    "validate_supported_dataset_kind",
]
