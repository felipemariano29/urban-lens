from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from urban_lens.core.settings import AppConfig
from urban_lens.workflows.doc_indexing import docs_to_vector_index


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
    knowledge_collection: list[dict[str, object]] = field(default_factory=list)
    knowledge_collection_created: bool = False

    def ensure_knowledge_collection(self) -> None:
        self.knowledge_collection_created = True

    def upsert_knowledge_chunks(self, records: list[dict[str, object]]) -> int:
        existing = {str(r["chunk_id"]): i for i, r in enumerate(self.knowledge_collection)}
        for record in records:
            chunk_id = str(record["chunk_id"])
            if chunk_id in existing:
                self.knowledge_collection[existing[chunk_id]] = record
            else:
                self.knowledge_collection.append(record)
        return len(records)


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]


class FakeMetadataStore:
    def __init__(self) -> None:
        self.pipeline_runs: dict[str, dict[str, object]] = {}
        self.audit_events: list[object] = []

    def register_pipeline_run(self, payload) -> str:
        run_id = str(uuid.uuid4())
        self.pipeline_runs[run_id] = {"status": payload.status}
        return run_id

    def finalize_pipeline_run(self, pipeline_run_id, status, output_versions, error_summary=None) -> None:
        self.pipeline_runs[pipeline_run_id]["status"] = status

    def register_audit_event(self, payload) -> str:
        self.audit_events.append(payload)
        return str(uuid.uuid4())


def test_docs_to_vector_index_writes_into_knowledge_collection(tmp_path) -> None:
    doc_path = tmp_path / "assistant-knowledge.md"
    doc_path.write_text(
        "# Title\n\n## Quem e voce\n\nUrban Lens e um assistente RAG local.\n",
        encoding="utf-8",
    )

    vector_store = FakeVectorStore()
    metadata_store = FakeMetadataStore()

    result = docs_to_vector_index(
        doc_paths=[doc_path],
        actor="test",
        config=FAKE_CONFIG,
        vector_store=vector_store,
        embedder=FakeEmbedder(),
        metadata_store=metadata_store,
    )

    assert result["indexed_count"] == 1
    assert vector_store.knowledge_collection_created is True
    assert len(vector_store.knowledge_collection) == 1
    record = vector_store.knowledge_collection[0]
    assert record["source_type"] == "docs"
    assert record["chunk_type"] == "documentation"
    assert record["reference"] == "docs:assistant-knowledge > Quem e voce"
    assert record["document_category"] == "platform"
    assert metadata_store.pipeline_runs[result["pipeline_run_id"]]["status"] == "completed"
