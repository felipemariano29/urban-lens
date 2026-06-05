"""Pipeline: Markdown documentation files → Ollama embeddings → Milvus index."""

from __future__ import annotations

from pathlib import Path

from urban_lens.core.settings import AppConfig
from urban_lens.governance.contracts import AuditEventPayload, PipelineRunPayload
from urban_lens.governance.store import MetadataStore
from urban_lens.infrastructure.doc_chunker import chunk_markdown_files
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.vector_store import MilvusVectorStore


def docs_to_vector_index(
    doc_paths: list[Path],
    actor: str,
    config: AppConfig,
    vector_store: MilvusVectorStore | None = None,
    embedder: OllamaEmbedder | None = None,
    metadata_store: MetadataStore | None = None,
    batch_size: int = 32,
) -> dict[str, object]:
    """Chunk Markdown files, embed via Ollama, and upsert into Milvus.

    Documentation chunks use chunk_type='documentation' and empty
    reference_month/lsoa_code fields. The crime_type field stores
    the document category (e.g. 'data_flow', 'training', 'architecture').
    """
    vector_store = vector_store or MilvusVectorStore(config.milvus_uri)
    embedder = embedder or OllamaEmbedder(config.ollama_base_url, config.embedding_model)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    doc_labels = [p.name for p in doc_paths]

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="docs_to_vector_index",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[],
        )
    )

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="embedding_indexing_started",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={"doc_files": doc_labels},
        )
    )

    chunks_frame = chunk_markdown_files(doc_paths)
    vector_store.ensure_collection()

    records = chunks_frame.to_dict("records")
    total_indexed = 0

    for batch_start in range(0, len(records), batch_size):
        batch = records[batch_start : batch_start + batch_size]
        texts = [str(r["content"]) for r in batch]
        embeddings = embedder.embed(texts)

        milvus_records = [
            {
                "chunk_id": r["chunk_id"],
                "chunk_type": r["chunk_type"],
                "reference_month": r["reference_month"],
                "lsoa_code": r["lsoa_code"],
                "crime_type": r["crime_type"],
                "title": r["title"],
                "content": r["content"],
                # No upstream dataset_version; use pipeline_run_id as stable reference.
                "dataset_version_id": pipeline_run_id[:36],
                "embedding": embedding,
            }
            for r, embedding in zip(batch, embeddings)
        ]
        total_indexed += vector_store.upsert_chunks(milvus_records)

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="embedding_indexing_finished",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={
                "doc_files": doc_labels,
                "indexed_count": total_indexed,
                "batch_size": batch_size,
            },
        )
    )
    metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", [])

    return {
        "pipeline_run_id": pipeline_run_id,
        "indexed_count": total_indexed,
        "doc_files": doc_labels,
    }
