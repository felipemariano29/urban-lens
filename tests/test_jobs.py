from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import pandas as pd
import pytest

from urban_lens.core.settings import AppConfig
from urban_lens.sources.police_uk import UnsupportedDatasetKindError
from urban_lens.workflows import bronze_to_silver, ingest_to_bronze, process_snapshot_directory, silver_to_gold


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
        self.lineage_edges: list[dict[str, object]] = []
        self.audit_events: list[dict[str, object]] = []
        self._run_counter = 0
        self._dataset_counter = 0
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
