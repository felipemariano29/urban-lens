"""Pipeline: Gold RAG crime_chunks → Ollama embeddings → Milvus index."""

from __future__ import annotations

from urban_lens.core.settings import AppConfig
from urban_lens.governance.contracts import AuditEventPayload, PipelineRunPayload
from urban_lens.governance.store import MetadataStore
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.object_store import MinIOStorage
from urban_lens.infrastructure.vector_store import MilvusVectorStore


def _embedding_input_for_record(record: dict[str, object]) -> str:
    parts = [
        f"title: {record['title']}",
        f"chunk_type: {record['chunk_type']}",
    ]
    if record.get("reference_month"):
        parts.append(f"reference_month: {record['reference_month']}")
    if record.get("lsoa_code"):
        parts.append(f"lsoa_code: {record['lsoa_code']}")
    if record.get("crime_type"):
        parts.append(f"crime_type: {record['crime_type']}")
    parts.append(f"content: {record['content']}")
    return "\n".join(parts)


def gold_to_vector_index(
    rag_object_key: str,
    rag_dataset_version_id: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    vector_store: MilvusVectorStore | None = None,
    embedder: OllamaEmbedder | None = None,
    metadata_store: MetadataStore | None = None,
    batch_size: int = 32,
) -> dict[str, object]:
    """Read crime_chunks from MinIO, generate embeddings via Ollama, and upsert into Milvus.

    Returns a dict with pipeline_run_id and total indexed_count.
    """
    storage = storage or MinIOStorage(config)
    vector_store = vector_store or MilvusVectorStore(config.milvus_uri)
    embedder = embedder or OllamaEmbedder(config.ollama_base_url, config.embedding_model)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="gold_to_vector_index",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[rag_dataset_version_id],
        )
    )

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="embedding_indexing_started",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={
                "rag_object_key": rag_object_key,
                "rag_dataset_version_id": rag_dataset_version_id,
            },
        )
    )

    chunks_frame = storage.read_parquet(rag_object_key)
    vector_store.ensure_collection()

    records = chunks_frame.to_dict("records")
    total_records = len(records)
    total_batches = (total_records + batch_size - 1) // batch_size
    total_indexed = 0

    for batch_num, batch_start in enumerate(range(0, total_records, batch_size), start=1):
        batch = records[batch_start : batch_start + batch_size]
        texts = [_embedding_input_for_record(r) for r in batch]
        embeddings = embedder.embed(texts)

        milvus_records = [
            {
                "chunk_id": r["chunk_id"],
                "chunk_type": r["chunk_type"],
                "reference_month": r["reference_month"],
                # lsoa_code is None for month_category chunks; Milvus VARCHAR cannot be null
                "lsoa_code": r.get("lsoa_code") or "",
                "crime_type": r.get("crime_type") or "",
                "title": r["title"],
                "content": r["content"],
                "dataset_version_id": rag_dataset_version_id,
                "embedding": embedding,
            }
            for r, embedding in zip(batch, embeddings)
        ]
        total_indexed += vector_store.upsert_chunks(milvus_records)
        print(f"  [{batch_num}/{total_batches}] {total_indexed}/{total_records} chunks indexados", flush=True)

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="embedding_indexing_finished",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={
                "rag_dataset_version_id": rag_dataset_version_id,
                "indexed_count": total_indexed,
                "batch_size": batch_size,
            },
        )
    )
    metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", [])

    return {
        "pipeline_run_id": pipeline_run_id,
        "indexed_count": total_indexed,
        "rag_dataset_version_id": rag_dataset_version_id,
    }
