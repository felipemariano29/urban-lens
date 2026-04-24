# ADR 0002: Embeddings and Vector Indexing Pipeline

## Status

Accepted

## Context

Urban-Lens already produces `gold/rag/crime_chunks` Parquet files via `build_rag_evidence_records()`. Those chunks are short evidence snippets (area+month+category, area+month, citywide+category) but they are not yet indexed anywhere for semantic retrieval. Completing the RAG loop requires:

1. A vector database to store and search embeddings.
2. An embedding model to convert chunk text to dense vectors.
3. A pipeline that connects Gold RAG output to the vector index, with the same governance guarantees (pipeline_run, audit trail, lineage) already used in the medallion pipeline.

## Decisions

### Vector database: Milvus Standalone

**Chosen**: `milvusdb/milvus:v2.4.9` running as a Docker Compose service.

**Why not Chroma or Qdrant**: Milvus is production-grade, supports HNSW indexes natively, has a mature Python client (`pymilvus`), and integrates with the existing MinIO instance for its own object storage — keeping the infrastructure footprint consistent.

Milvus requires `etcd` for metadata. The standalone image ships with an embedded etcd process, configured via `docker/milvus/user.yaml` (`etcd.use.embed: true`). No separate etcd service is needed. MinIO is reused with a dedicated `milvus` bucket (created by `minio-setup`).

### Embedding model: nomic-embed-text via Ollama

**Chosen**: `nomic-embed-text` served by `ollama/ollama:latest`.

**Why**: Runs fully locally (no API key, no egress), produces 768-dimensional vectors, scores competitively against OpenAI ada-002 on retrieval benchmarks, and is the canonical embedding model recommended by the Ollama project for RAG use cases.

The `ollama-setup` service pulls the model automatically on first run.

### Collection schema

Collection name: `crime_chunks`

| Field | Type | Notes |
|---|---|---|
| `chunk_id` | VARCHAR(64) | SHA-256 hex digest; deterministic from content |
| `chunk_type` | VARCHAR(32) | `area_month_category`, `area_month`, `month_category` |
| `reference_month` | VARCHAR(7) | `YYYY-MM` |
| `lsoa_code` | VARCHAR(16) | Empty string for `month_category` chunks (Milvus VARCHAR cannot be null) |
| `crime_type` | VARCHAR(64) | Normalized snake_case |
| `title` | VARCHAR(512) | Human-readable summary used as chunk title |
| `content` | VARCHAR(65535) | Text passed to the embedding model |
| `dataset_version_id` | VARCHAR(36) | UUID of the upstream `crime_chunks` dataset_version |
| `embedding` | FLOAT_VECTOR(768) | nomic-embed-text output |

### Index: HNSW with COSINE metric

**HNSW** is chosen over IVF_FLAT because it provides approximate nearest-neighbour search with sub-linear query time and no separate training step. Parameters `M=16, efConstruction=200` follow the Milvus recommended defaults for medium-sized corpora.

**COSINE** similarity is preferred over L2 because embedding magnitude varies across chunk lengths; cosine measures directional similarity and is more robust for semantic retrieval over variable-length text.

### Batch size: 32

Ollama's `/api/embed` endpoint accepts multiple inputs in one call. Batching 32 texts per request balances throughput (fewer HTTP round-trips) against memory pressure on the Ollama process running on CPU. This can be overridden via `--batch-size` CLI flag or the `BATCH_SIZE` Makefile variable.

### Governance: audit events, no new dataset_version for the vector index

The Milvus collection is a **mutable upsert target**, not an immutable object in MinIO. Forcing it into `dataset_versions` (which is designed for immutable, content-hashed artifacts) would require either relaxing the uniqueness constraint or generating a synthetic object_path per run.

Instead, each indexing run is tracked via:
- A `pipeline_run` record (`gold_to_vector_index`)
- Two audit events: `embedding_indexing_started` and `embedding_indexing_finished`
- The `rag_dataset_version_id` stored in every Milvus chunk for downstream traceability

This keeps the governance model consistent without retrofitting the `dataset_versions` table for a different storage paradigm.

### lsoa_code null handling

`month_category` chunks have `lsoa_code = None` because they aggregate citywide statistics. Milvus VARCHAR fields do not accept null values. The pipeline stores an empty string `""` as a sentinel. Retrieval code must treat `""` as "no area filter" when filtering by lsoa_code.

## Consequences

Positive:
- Semantic search over crime evidence is now possible
- Fully local — no external API dependencies
- Upsert semantics allow safe re-indexing without duplicating chunks
- Governance audit trail covers every indexing run

Trade-offs:
- Milvus + etcd add two new Docker services and increase memory requirements (~2 GB additional RAM recommended)
- Ollama on CPU is slow for large corpora; first-time model pull requires internet access
- `nomic-embed-text` is English-only; if the data description language changes, a different model is needed

## Follow-up

- Implement the retrieval step (`VectorStore.search()` is already stubbed)
- Add `POST /api/v1/chat/query` endpoint that uses retrieval + Ollama generation
- Consider Attu (Milvus web UI) for collection inspection during development
