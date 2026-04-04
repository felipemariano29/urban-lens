# Implementation Guide

## Scope

This guide covers the governance and medallion tasks implemented in this repository:
- metadata and lineage contract
- PostgreSQL governance schema
- Bronze to Silver to Gold pipeline
- Gold ML dataset generation
- baseline forecast-model training

Current ingestion scope:
- the MVP pipeline supports `DATA.POLICE.UK` `street` CSV files
- `outcomes` and `stop-and-search` CSVs are detected and rejected explicitly
- mixed monthly snapshot folders can be scanned and filtered so only supported `street` files are processed

## Repository Components

- `docs/architecture/metadata-contract.md`: cross-team governance contract
- `docs/architecture/medallion-governance.md`: medallion architecture and chat runtime policy
- `docs/adr/0001-medallion-layout.md`: design decision for Gold segmentation
- `sql/init/001_governance_schema.sql`: PostgreSQL schema for metadata, lineage, audit, access, and model versions
- `src/urban_lens/sources/police_uk/transformations.py`: source classification, normalization, and Gold dataset builders
- `src/urban_lens/forecasting/features.py`: Gold ML feature generation
- `src/urban_lens/workflows/`: orchestration jobs split by workflow
- `src/urban_lens/governance/`: metadata contracts, store, and ORM models
- `src/urban_lens/infrastructure/`: object storage and database adapters
- `pipelines/*.py`: CLI entrypoints

## Environment Variables

Copy `.env.example` into your environment or export the variables before running the jobs.

Required services:
- MinIO for object storage
- PostgreSQL for governance metadata
- MLflow for model tracking

## Recommended Execution Order

### 1. Apply the governance schema

Run `sql/init/001_governance_schema.sql` in PostgreSQL before any pipeline job.

### 2. Install the package

```bash
python3 -m pip install -e ".[dev]"
```

### 3. Ingest a CSV into Bronze

```bash
python3 pipelines/ingest_manual.py \
  --csv-path /absolute/path/to/2024-01-street.csv \
  --force-name metropolitan \
  --actor kaique.govani
```

The ingestion command expects a `street` CSV in the shape published by `DATA.POLICE.UK`.
If you point it to an `outcomes` or `stop-and-search` file, the job will fail with a validation error and record that failure in governance metadata.

### 3a. Process an entire monthly snapshot folder

```bash
python3 pipelines/process_snapshot.py \
  --snapshot-dir /absolute/path/to/data/2026-01 \
  --actor kaique.govani
```

This command scans a snapshot directory, selects supported `street` CSV files, and skips unsupported file families.

### 4. Transform Bronze into Silver

```bash
python3 pipelines/bronze_to_silver.py \
  --bronze-object-key bronze/data.police.uk/crimes/year=2024/month=01/force=metropolitan/2024-01-street.csv \
  --bronze-dataset-version-id <bronze_dataset_version_id> \
  --actor kaique.govani
```

### 5. Publish Gold analytics, RAG, and ML datasets

```bash
python3 pipelines/silver_to_gold.py \
  --silver-object-key silver/police_uk/crimes_standardized/year=2024/month=01/part-000.parquet \
  --silver-dataset-version-id <silver_dataset_version_id> \
  --actor kaique.govani
```

### 6. Train the baseline forecast model

```bash
python3 pipelines/train_forecast_model.py \
  --training-object-key gold/ml/forecast_training_set/year=2024/month=01/part-000.parquet \
  --training-dataset-version-id <training_dataset_version_id> \
  --scoring-object-key gold/ml/forecast_scoring_set/year=2024/month=01/part-000.parquet \
  --scoring-dataset-version-id <scoring_dataset_version_id> \
  --actor kaique.govani
```

## What the Pipeline Produces

The current implementation publishes:
- raw Bronze CSV objects
- standardized Silver parquet
- Gold analytics datasets for area/month/category, area/month, and month/category
- Gold RAG evidence chunks
- Gold ML training and scoring sets
- forecast predictions for the latest available horizon

It also registers:
- dataset versions
- pipeline runs
- lineage edges
- audit events
- access policies
- model versions

## Test Coverage

Current automated tests validate:
- CSV normalization and month inference
- classification of real `DATA.POLICE.UK` snapshot files
- rejection of unsupported `outcomes` and `stop-and-search` datasets
- Gold analytical aggregations
- Gold ML feature generation and next-period target creation
- end-to-end Bronze to Silver to Gold orchestration with fake storage and metadata

Run the tests with:

```bash
python3 -m pytest
```
