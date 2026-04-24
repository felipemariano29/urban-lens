"""Tests for the embeddings and indexing pipeline."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from urban_lens.core.settings import AppConfig
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.workflows.embeddings import gold_to_vector_index


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CONFIG = AppConfig(
    s3_endpoint_url="http://localhost:9000",
    s3_access_key="test",
    s3_secret_key="test",
    s3_bucket="test",
    s3_region="us-east-1",
    s3_secure=False,
    postgres_dsn="postgresql://test:test@localhost:5432/test",
    mlflow_tracking_uri="http://localhost:5005",
    artifact_dir=Path(".artifacts"),
    milvus_uri="http://localhost:19530",
    ollama_base_url="http://localhost:11434",
    embedding_model="nomic-embed-text",
)


@dataclass
class FakeVectorStore:
    collections: dict[str, list[dict]] = field(default_factory=dict)

    def ensure_collection(self) -> None:
        self.collections.setdefault("crime_chunks", [])

    def upsert_chunks(self, records: list[dict]) -> int:
        self.collections.setdefault("crime_chunks", [])
        existing = {r["chunk_id"]: i for i, r in enumerate(self.collections["crime_chunks"])}
        for record in records:
            if record["chunk_id"] in existing:
                self.collections["crime_chunks"][existing[record["chunk_id"]]] = record
            else:
                self.collections["crime_chunks"].append(record)
        return len(records)

    def count(self) -> int:
        return len(self.collections.get("crime_chunks", []))

    def search(self, query_embedding, top_k=5, filters=None):
        return []


@dataclass
class FakeEmbedder:
    dim: int = 768
    call_count: int = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return [[0.1] * self.dim for _ in texts]

    def health_check(self) -> bool:
        return True


@dataclass
class FakeStorage:
    parquet_objects: dict[str, pd.DataFrame] = field(default_factory=dict)

    def read_parquet(self, object_key: str) -> pd.DataFrame:
        return self.parquet_objects[object_key].copy()

    def write_parquet(self, df: pd.DataFrame, object_key: str) -> None:
        self.parquet_objects[object_key] = df.copy()


class FakeMetadataStore:
    def __init__(self) -> None:
        self.pipeline_runs: dict[str, dict] = {}
        self.audit_events: list[dict] = []

    def register_pipeline_run(self, payload) -> str:
        run_id = str(uuid.uuid4())
        self.pipeline_runs[run_id] = {"payload": payload, "status": payload.status}
        return run_id

    def finalize_pipeline_run(self, pipeline_run_id, status, output_versions, error_summary=None):
        self.pipeline_runs[pipeline_run_id]["status"] = status

    def register_audit_event(self, payload) -> str:
        event_id = str(uuid.uuid4())
        self.audit_events.append({"id": event_id, "payload": payload})
        return event_id

    def register_dataset_version(self, payload) -> str:
        return str(uuid.uuid4())

    def list_dataset_versions(self, **kwargs):
        return []


def _sample_rag_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "chunk_id": "a" * 64,
                "chunk_type": "area_month_category",
                "reference_month": "2026-01",
                "lsoa_code": "E01000001",
                "crime_type": "burglary",
                "title": "2026-01 Some Area burglary",
                "content": "In 2026-01, area Some Area (E01000001) recorded 5 incidents.",
            },
            {
                "chunk_id": "b" * 64,
                "chunk_type": "area_month",
                "reference_month": "2026-01",
                "lsoa_code": "E01000001",
                "crime_type": "burglary",
                "title": "2026-01 Some Area overview",
                "content": "In 2026-01, area Some Area recorded 10 incidents across 2 types.",
            },
            {
                "chunk_id": "c" * 64,
                "chunk_type": "month_category",
                "reference_month": "2026-01",
                "lsoa_code": None,
                "crime_type": "burglary",
                "title": "2026-01 citywide burglary",
                "content": "In 2026-01, crime type burglary recorded 100 incidents.",
            },
        ]
    )


# ---------------------------------------------------------------------------
# OllamaEmbedder unit tests
# ---------------------------------------------------------------------------


class TestOllamaEmbedder:
    def test_embed_returns_correct_shape(self):
        body = json.dumps({"embeddings": [[0.1] * 768, [0.2] * 768]}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = body
        mock_cm.__enter__.return_value.status = 200

        with patch("urllib.request.urlopen", return_value=mock_cm):
            embedder = OllamaEmbedder("http://localhost:11434")
            result = embedder.embed(["text one", "text two"])

        assert len(result) == 2
        assert len(result[0]) == 768
        assert len(result[1]) == 768

    def test_embed_empty_list_returns_empty(self):
        embedder = OllamaEmbedder("http://localhost:11434")
        assert embedder.embed([]) == []

    def test_embed_sends_correct_payload(self):
        body = json.dumps({"embeddings": [[0.0] * 768]}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = body
        mock_cm.__enter__.return_value.status = 200

        captured: list[dict] = []

        def fake_urlopen(req, timeout=None):
            captured.append(json.loads(req.data.decode()))
            return mock_cm

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            OllamaEmbedder("http://localhost:11434", model="my-model").embed(["hello"])

        assert captured[0]["model"] == "my-model"
        assert captured[0]["input"] == ["hello"]

    def test_health_check_success(self):
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.status = 200

        with patch("urllib.request.urlopen", return_value=mock_cm):
            assert OllamaEmbedder("http://localhost:11434").health_check() is True

    def test_health_check_connection_failure(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            assert OllamaEmbedder("http://localhost:11434").health_check() is False


# ---------------------------------------------------------------------------
# gold_to_vector_index workflow tests
# ---------------------------------------------------------------------------


class TestGoldToVectorIndex:
    def _run(self, frame: pd.DataFrame, batch_size: int = 10) -> tuple[dict, FakeVectorStore, FakeEmbedder, FakeMetadataStore]:
        key = "gold/rag/crime_chunks/year=2026/month=01/part-000.parquet"
        version_id = str(uuid.uuid4())

        storage = FakeStorage()
        storage.parquet_objects[key] = frame
        vector_store = FakeVectorStore()
        embedder = FakeEmbedder()
        metadata_store = FakeMetadataStore()

        result = gold_to_vector_index(
            rag_object_key=key,
            rag_dataset_version_id=version_id,
            actor="test",
            config=FAKE_CONFIG,
            storage=storage,
            vector_store=vector_store,
            embedder=embedder,
            metadata_store=metadata_store,
            batch_size=batch_size,
        )
        return result, vector_store, embedder, metadata_store

    def test_indexes_all_chunks(self):
        result, vector_store, _, _ = self._run(_sample_rag_frame())
        assert result["indexed_count"] == 3
        assert vector_store.count() == 3

    def test_batching_splits_embed_calls(self):
        _, _, embedder, _ = self._run(_sample_rag_frame(), batch_size=2)
        # 3 chunks in batches of 2 → ceil(3/2) = 2 embed calls
        assert embedder.call_count == 2

    def test_pipeline_run_completed(self):
        result, _, _, metadata_store = self._run(_sample_rag_frame())
        run_id = result["pipeline_run_id"]
        assert metadata_store.pipeline_runs[run_id]["status"] == "completed"

    def test_audit_events_emitted(self):
        _, _, _, metadata_store = self._run(_sample_rag_frame())
        event_types = [e["payload"].event_type for e in metadata_store.audit_events]
        assert "embedding_indexing_started" in event_types
        assert "embedding_indexing_finished" in event_types

    def test_null_lsoa_stored_as_empty_string(self):
        _, vector_store, _, _ = self._run(_sample_rag_frame())
        chunks = vector_store.collections["crime_chunks"]
        month_cat = next(c for c in chunks if c["chunk_type"] == "month_category")
        assert month_cat["lsoa_code"] == ""

    def test_dataset_version_id_propagated_to_chunks(self):
        key = "gold/rag/crime_chunks/year=2026/month=01/part-000.parquet"
        version_id = str(uuid.uuid4())
        storage = FakeStorage()
        storage.parquet_objects[key] = _sample_rag_frame()
        vector_store = FakeVectorStore()

        gold_to_vector_index(
            rag_object_key=key,
            rag_dataset_version_id=version_id,
            actor="test",
            config=FAKE_CONFIG,
            storage=storage,
            vector_store=vector_store,
            embedder=FakeEmbedder(),
            metadata_store=FakeMetadataStore(),
        )

        for chunk in vector_store.collections["crime_chunks"]:
            assert chunk["dataset_version_id"] == version_id

    def test_upsert_replaces_existing_chunk(self):
        frame = _sample_rag_frame()
        key = "gold/rag/crime_chunks/year=2026/month=01/part-000.parquet"
        version_id = str(uuid.uuid4())
        storage = FakeStorage()
        storage.parquet_objects[key] = frame
        vector_store = FakeVectorStore()
        embedder = FakeEmbedder()
        meta = FakeMetadataStore()

        gold_to_vector_index(
            rag_object_key=key, rag_dataset_version_id=version_id,
            actor="test", config=FAKE_CONFIG,
            storage=storage, vector_store=vector_store,
            embedder=embedder, metadata_store=meta,
        )
        first_count = vector_store.count()

        # Second run with same data → upsert, count must not grow
        storage.parquet_objects[key] = frame
        gold_to_vector_index(
            rag_object_key=key, rag_dataset_version_id=version_id,
            actor="test", config=FAKE_CONFIG,
            storage=storage, vector_store=vector_store,
            embedder=embedder, metadata_store=meta,
        )
        assert vector_store.count() == first_count
