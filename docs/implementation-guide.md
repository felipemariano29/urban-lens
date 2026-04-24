# Implementation Guide

## Scope

This guide covers every step to run the Urban-Lens pipeline from a clean environment to a queryable RAG corpus:
- metadata and lineage contract
- PostgreSQL governance schema
- Bronze to Silver to Gold pipeline
- Gold ML dataset generation and baseline forecast training
- Embedding indexing (crime data and documentation)

Current ingestion scope:
- the MVP pipeline supports `DATA.POLICE.UK` `street` CSV files
- `outcomes` and `stop-and-search` CSVs are detected and rejected explicitly
- mixed monthly snapshot folders can be scanned and filtered so only supported `street` files are processed

## Repository Components

- `docs/architecture/metadata-contract.md`: cross-team governance contract
- `docs/architecture/medallion-governance.md`: medallion architecture and chat runtime policy
- `docs/data-flow.md`: end-to-end data flow reference
- `docs/training-process.md`: ML training process and evaluation criteria
- `docs/adr/0001-medallion-layout.md`: design decision for Gold segmentation
- `docs/adr/0002-embeddings-indexing.md`: design decisions for Milvus, Ollama, and HNSW index
- `sql/init/001_governance_schema.sql`: PostgreSQL schema for metadata, lineage, audit, access, and model versions
- `src/urban_lens/sources/police_uk/transformations.py`: source classification, normalization, and Gold dataset builders
- `src/urban_lens/forecasting/features.py`: Gold ML feature generation
- `src/urban_lens/workflows/`: orchestration jobs split by workflow
- `src/urban_lens/infrastructure/`: object storage, vector store, embedder, and database adapters
- `src/urban_lens/governance/`: metadata contracts, store, and ORM models

## Required Services

Copy `.env.example` into `.env` and configure credentials before starting the stack.

Start all services with:

```bash
make up
```

Required services and their roles:

| Service | Purpose | Default port |
|---|---|---|
| PostgreSQL | Governance metadata, lineage, audit, access policies | 5432 |
| MinIO | Data lake (Bronze, Silver, Gold Parquet and CSV artifacts) | 9012 |
| MLflow | Experiment tracking and model artifact storage | 5005 |
| Milvus | Vector index for crime evidence and documentation chunks | 19530 |
| Ollama | Local LLM and embedding model server | 11434 |

On first startup, `minio-setup` creates the `urban-lens` and `milvus` buckets, and `ollama-setup` downloads the `nomic-embed-text` embedding model. The model download requires internet access and may take several minutes.

Show all service URLs:

```bash
make urls
```

## Install the Package

```bash
make install
```

Or manually:

```bash
python3 -m pip install -e ".[dev]"
```

## Recommended Execution Order

### 1. Apply the governance schema

The SQL schema is applied automatically when PostgreSQL starts via the `sql/init/` mount. To apply manually:

```bash
psql $URBAN_LENS_POSTGRES_DSN -f sql/init/001_governance_schema.sql
```

### 2. Ingest a CSV into Bronze

Single file:

```bash
make ingest-manual CSV_PATH=/path/to/2026-01-metropolitan-street.csv FORCE_NAME=metropolitan
```

Or process an entire monthly snapshot folder (recommended):

```bash
make process-snapshot SNAPSHOT_DIR=data/2026-01
```

This command scans the folder, selects supported `street` CSV files, and skips unsupported file families. Use `make ingest-all` to process every snapshot in `data/`.

### 3. Transform Bronze into Silver

```bash
make bronze-to-silver \
  BRONZE_OBJECT_KEY=bronze/data.police.uk/crimes/year=2026/month=01/force=metropolitan/2026-01-metropolitan-street.csv \
  BRONZE_DATASET_VERSION_ID=<id printed by step 2>
```

### 4. Publish Gold analytics, RAG, and ML datasets

```bash
make silver-to-gold \
  SILVER_OBJECT_KEY=silver/police_uk/crimes_standardized/year=2026/month=01/part-000.parquet \
  SILVER_DATASET_VERSION_ID=<id printed by step 3>
```

This step produces: three Gold analytics Parquet files, one Gold RAG crime_chunks Parquet, and two Gold ML Parquet files (training set and scoring set).

### 5. Index crime evidence into Milvus

```bash
make index-embeddings-latest
```

Reads the most recent `crime_chunks` dataset, generates embeddings via Ollama (`nomic-embed-text`), and upserts into Milvus. Specify `VERSION=2026-01` to index a particular month. Use `BATCH_SIZE=16` to reduce memory pressure on CPU-only machines.

### 6. Index documentation into Milvus

```bash
make index-docs
```

Reads all Markdown files in `docs/`, splits them by H2 heading, and indexes each section as a `documentation` chunk in Milvus. This makes architecture and process documentation queryable via RAG.

### 7. Train the baseline forecast model

```bash
make train-latest
```

Discovers the most recent Gold ML training and scoring datasets, trains three regression candidates (Ridge, RandomForest, ExtraTreesRegressor), evaluates on a temporal holdout, logs all runs to MLflow, and publishes forecast predictions for the next period.

Run with explicit dataset IDs:

```bash
make train-forecast \
  TRAINING_OBJECT_KEY=gold/ml/forecast_training_set/year=2026/month=01/part-000.parquet \
  TRAINING_DATASET_VERSION_ID=<id> \
  SCORING_OBJECT_KEY=gold/ml/forecast_scoring_set/year=2026/month=01/part-000.parquet \
  SCORING_DATASET_VERSION_ID=<id>
```

## What the Pipeline Produces

| Artifact | Storage | Description |
|---|---|---|
| Bronze CSV | MinIO | Immutable raw source file |
| Silver Parquet | MinIO | Normalized occurrence-level records |
| Gold analytics (×3) | MinIO | Area/month/category aggregations |
| Gold RAG crime_chunks | MinIO | Short evidence snippets for retrieval |
| Gold ML training set | MinIO | Engineered features + target |
| Gold ML scoring set | MinIO | Engineered features (no target) |
| Forecast predictions | MinIO | Next-period incident count estimates |
| Vector index | Milvus | Embedded crime chunks and documentation |
| Experiment runs | MLflow | Model parameters, metrics, and artifacts |
| Governance metadata | PostgreSQL | dataset_versions, pipeline_runs, lineage_edges, audit_events, model_versions |

## Test Coverage

Run all tests:

```bash
make test
```

Or directly:

```bash
python3 -m pytest
```

Current automated tests validate:
- CSV normalization and month inference
- classification of real `DATA.POLICE.UK` snapshot files
- rejection of unsupported `outcomes` and `stop-and-search` datasets
- Gold analytical aggregations
- Gold ML feature generation and next-period target creation
- end-to-end Bronze to Silver to Gold orchestration with fake storage and metadata
- OllamaEmbedder HTTP payload and response parsing
- gold_to_vector_index batching, governance registration, and upsert idempotency

## Smoke Test Procedure

Use the January 2026 snapshot already present in the repository:

```bash
make process-snapshot SNAPSHOT_DIR=data/2026-01 ACTOR=smoke-test
make index-embeddings-latest ACTOR=smoke-test
make index-docs ACTOR=smoke-test
make train-latest ACTOR=smoke-test
```

Validate success by checking:
- MinIO console: Silver and Gold Parquet files exist for `year=2026/month=01`
- MLflow UI: a completed experiment run appears under `crime_forecasting`
- Milvus: the `crime_chunks` collection has records (check with `make urls` → Milvus REST)
- PostgreSQL: `SELECT COUNT(*) FROM governance.dataset_versions` returns non-zero rows
