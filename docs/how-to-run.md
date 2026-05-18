# Urban-Lens Run Guide

This guide explains how to start the local infrastructure and where to find the correct documentation for the governed data pipeline.

For Sprint 3, the repository already contains a working Bronze -> Silver -> Gold pipeline implementation plus governance metadata registration. This document is the entry point. The detailed execution flow lives in the documents referenced below.

## What This Guide Covers

- local infrastructure startup
- database bootstrap location
- Python environment setup for pipeline jobs
- links to the authoritative data-pipeline execution and governance documents

## Documentation Map

Use these documents together:

| Document | Purpose |
| --- | --- |
| `docs/how-to-run.md` | Local environment startup and navigation hub |
| `docs/how-to-populate-db.md` | How PostgreSQL initialization scripts work |
| `docs/implementation-guide.md` | Step-by-step pipeline execution order |
| `docs/ac2-sprint-closure.md` | Formal AC2 closure mapping for Sprints 1 to 8 |
| `docs/architecture/medallion-governance.md` | Layer rules, path conventions, quality gates, and allowed data movement |
| `docs/architecture/metadata-contract.md` | Governance entities, lineage, audit, access, and response contracts |
| `docs/adr/0001-medallion-layout.md` | Why Gold is segmented across analytics, RAG, and ML |

## Current Runtime Scope

The repository currently provides:

- PostgreSQL for governance metadata
- pgAdmin for database inspection
- MinIO for object storage
- MinIO bucket bootstrap via `minio-setup`
- MLflow for experiment tracking and model registry UI
- Attu for Milvus collection inspection
- FastAPI internal API via `rag-api`
- Next.js frontend with server-side proxy routes under `app/api/v1/*`
- Python pipeline jobs for Bronze, Silver, Gold, and forecast-model publication

The repository now provisions the local platform components required by the implemented pipeline and RAG runtime, including Milvus and Ollama inside Docker Compose.

## Repository Structure

```bash
.
├── docker-compose.yml
├── Makefile
├── sql/init/
├── pipelines/
├── src/urban_lens/
├── tests/
└── docs/
    ├── how-to-run.md
    ├── how-to-populate-db.md
    ├── implementation-guide.md
    └── architecture/
```

## Prerequisites

Make sure these tools are installed locally:

- Docker
- Docker Compose
- GNU Make
- Git
- Python 3.11+
- `pip`

Recommended:

- 8 GB+ RAM
- 2+ CPU cores

## Environment Setup

1. Clone the repository:

```bash
git clone https://github.com/felipemariano29/urban-lens.git
cd urban-lens
```

2. Create the environment file:

```bash
cp .env.example .env
```

3. Review the values in `.env` if you need different ports or credentials.
   The frontend proxy also reads:
   - `URBAN_LENS_API_BASE_URL` for the FastAPI base URL
   - `URBAN_LENS_INTERNAL_API_KEY` for server-side authenticated proxy calls
   - `URBAN_LENS_CHAT_MODEL` for the default Ollama chat model
   - `OLLAMA_MODELS` for the list of Ollama models pre-downloaded by `ollama-setup`

4. Install the Python package used by the pipeline jobs:

```bash
python3 -m pip install -e ".[dev]"
```

## Start Local Infrastructure

Start the available containers with:

```bash
make up
```

Or directly:

```bash
docker compose up -d
```

For explicit mode selection:

```bash
make up-cpu
make up-gpu
```

This starts:

- PostgreSQL
- pgAdmin
- MinIO
- MinIO bucket bootstrap
- MLflow
- Milvus
- Attu
- Ollama
- rag-api
- frontend

Run `make fullstack` to start the full Docker stack and then print the local URLs.
The Docker Compose stack now waits for healthchecks and one-shot setup containers before starting downstream services, reducing cold-start race conditions between PostgreSQL, MinIO, MLflow, Milvus, Ollama, and the API.

If you need to run the frontend outside Docker for local UI development, use:

```bash
make frontend
```

## Available Services

### PostgreSQL

- Host: `localhost`
- Port: `${POSTGRES_HOST_PORT:-5432}`

### pgAdmin

- URL: `http://localhost:${PGADMIN_HOST_PORT:-5050}`
- Login email: `PGADMIN_DEFAULT_EMAIL`
- Login password: `PGADMIN_DEFAULT_PASSWORD`

The PostgreSQL server is pre-registered as `Urban Lens Postgres`.

### MinIO

- API: `http://localhost:${MINIO_API_HOST_PORT:-9012}`
- Console: `http://localhost:${MINIO_CONSOLE_HOST_PORT:-9003}`

Credentials are defined in `.env`.

### rag-api

- Base URL: `http://localhost:${RAG_API_HOST_PORT:-8000}`
- Health check: `http://localhost:${RAG_API_HOST_PORT:-8000}/api/v1/health`
- Ollama models endpoint: `http://localhost:${RAG_API_HOST_PORT:-8000}/api/v1/system/models`

### Attu

- URL: `http://localhost:${ATTU_HOST_PORT:-3001}`
- Milvus target: `milvus-standalone:19530`
- Purpose: inspect collections such as `crime_chunks`, confirm row counts, and explore schema during local validation

### Frontend

- URL: `http://localhost:${WEB_HOST_PORT:-3000}`
- The browser calls Next.js route handlers first, and those handlers proxy to FastAPI using the server-side API key.
- The query sidebar now loads available Ollama models from the local API and lets the user choose the generation model per request.

### MLflow

- URL: `http://localhost:${MLFLOW_HOST_PORT:-5005}`
- Artifacts: stored in MinIO under `s3://<bucket>/mlflow`

## Governance Schema Bootstrap

PostgreSQL loads SQL files from `sql/init/` on first startup because that directory is mounted into `/docker-entrypoint-initdb.d`.

The governance schema used by the pipeline is:

- `sql/init/001_governance_schema.sql`

For details on naming, ordering, and re-running initialization scripts, see:

- `docs/how-to-populate-db.md`

Important:

- initialization scripts run only when the database volume is created
- if you need to re-run them, reset the environment with `make reset`

## Data Pipeline Execution

The authoritative runbook for the data pipeline is:

- `docs/implementation-guide.md`

That document defines the exact execution order for:

1. applying the governance schema
2. ingesting a `DATA.POLICE.UK` `street` CSV into Bronze
3. processing a monthly snapshot directory
4. transforming Bronze into Silver
5. publishing Gold analytics, RAG, and ML datasets
6. training and publishing forecast outputs

### Current MVP Data Scope

The implemented MVP pipeline currently supports:

- `DATA.POLICE.UK` `street` CSV files

The pipeline currently rejects:

- `outcomes` CSV files
- `stop-and-search` CSV files

This is intentional and documented in:

- `docs/implementation-guide.md`
- `docs/architecture/medallion-governance.md`

### Pipeline Entrypoints

The runnable CLI entrypoints are:

- `pipelines/ingest_manual.py`
- `pipelines/process_snapshot.py`
- `pipelines/bronze_to_silver.py`
- `pipelines/silver_to_gold.py`
- `pipelines/train_forecast_model.py`

### Layer Responsibilities

Use `docs/architecture/medallion-governance.md` as the source of truth for layer behavior:

- Bronze: immutable raw CSV objects plus metadata registration
- Silver: occurrence-level normalized parquet
- Gold Analytics: aggregated factual datasets
- Gold RAG: evidence-oriented text chunks
- Gold ML: training, scoring, and prediction datasets

## Useful Commands

```bash
make help
make up
make up-cpu
make up-gpu
make down
make reset
make logs
make logs-core
make logs-app
docker compose ps
python3 -m pytest
```

## Validation

Run the automated tests with:

```bash
python3 -m pytest
```

These tests validate:

- CSV normalization
- dataset-family classification
- rejection of unsupported file families
- Gold aggregations
- cumulative Gold ML dataset generation
- ML feature generation
- forecast-model candidate tracking
- end-to-end Bronze -> Silver -> Gold orchestration with fake storage and metadata

## Troubleshooting

### Containers do not start

```bash
docker compose logs -f
```

### Missing `.env`

```bash
cp .env.example .env
```

### Need to re-run database initialization

```bash
make reset
```

Warning: this removes volumes and deletes local container data.

### Pipeline command fails after infrastructure is up

Check:

- whether PostgreSQL is reachable through `URBAN_LENS_POSTGRES_DSN`
- whether MinIO is reachable through `URBAN_LENS_S3_ENDPOINT_URL`
- whether the bucket configured in `URBAN_LENS_S3_BUCKET` exists
- whether MLflow is reachable through `MLFLOW_TRACKING_URI`
- whether the governance schema was initialized successfully

## Next Reading

After this guide, read:

1. `docs/implementation-guide.md`
2. `docs/architecture/medallion-governance.md`
3. `docs/architecture/metadata-contract.md`
