# Urban-Lens Data Flow: End-to-End Reference

## Document purpose

This document describes the complete end-to-end data flow of Urban-Lens, covering every step from raw CSV ingestion through Bronze, Silver, and Gold layers to analytics consumption, RAG retrieval, ML training, and embedding indexing. Each section maps to a concrete pipeline step and its governance side effects.

## Source data

Urban-Lens ingests monthly crime data from DATA.POLICE.UK. The supported format is the "street" crime CSV, which contains one row per reported crime incident. Outcomes and stop-and-search CSVs are rejected at the ingestion boundary with an explicit validation error. The pipeline expects these columns: Crime ID, Reported by, Falls within, Longitude, Latitude, LSOA code, LSOA name, Crime type, Last outcome category, Context, Month, Location.

## Bronze ingestion

The ingestion job uploads a raw street CSV to MinIO without any transformation. The object is stored at `bronze/data.police.uk/crimes/year=YYYY/month=MM/force=<force>/<file>.csv`. A dataset_version record is created in PostgreSQL with the object path, row count, and content hash. Audit events ingest_started and ingest_finished are emitted. Bronze objects are immutable after publication and are the source of truth for replay. CLI: `urban-lens-ingest` or `make ingest-manual`.

## Silver normalization

The silver job reads a Bronze CSV from MinIO and produces a Parquet file at `silver/police_uk/crimes_standardized/year=YYYY/month=MM/part-000.parquet`. Normalization steps: column names are converted to snake_case, crime_type and last_outcome_category are normalized to stable lowercase keys, longitude and latitude are cast to numeric, reference_month is inferred from the Month column or the source file path, a deterministic record_hash is computed for each row, and duplicate rows are removed by hash. A lineage edge is registered from the Bronze dataset_version to the new Silver dataset_version. CLI: `urban-lens-bronze-to-silver` or `make bronze-to-silver`.

## Gold analytics publication

The gold job reads Silver and produces three analytics Parquet files. crime_metrics_area_month_category (grain: lsoa_code + reference_month + crime_type) contains incident counts, outcome ratios, and context ratios per area-period-type. crime_metrics_area_month (grain: lsoa_code + reference_month) adds the dominant crime type per area. crime_metrics_month_category (grain: reference_month + crime_type) provides citywide rankings. Paths follow `gold/analytics/<product>/year=YYYY/month=MM/part-000.parquet`. Each artifact gets a dataset_version and lineage edge from Silver. CLI: `urban-lens-silver-to-gold`.

## Gold RAG publication

The same silver-to-gold job also produces crime_chunks at `gold/rag/crime_chunks/year=YYYY/month=MM/part-000.parquet`. Each chunk has a chunk_id, chunk_type (area_month_category, area_month, or month_category), title, and content field containing a short human-readable evidence sentence. For example: "In 2026-01, area Westminster 001A (E01004736) recorded 12 incidents for crime type burglary. Outcome-known ratio was 0.58." Chunks are the input for the embedding indexing step and the retrieval context for RAG answers.

## Gold ML publication

The silver-to-gold job also builds the ML datasets. forecast_training_set contains engineered features with lag values (lag_1, lag_2, lag_3), moving averages (3 and 6 periods), seasonality fields (month_number, quarter), and the target incident_count_next_period. forecast_scoring_set has the same features but without the target, for inference. Both are stored at `gold/ml/<product>/year=YYYY/month=MM/part-000.parquet`. The training set is built from all available Gold analytics versions across the full historical archive, up to and including the current month. CLI: `urban-lens-silver-to-gold`.

## Embedding indexing

The indexing job reads crime_chunks from MinIO, sends texts to Ollama in batches for embedding with nomic-embed-text (768 dimensions), and upserts vectors into the Milvus crime_chunks collection. Each Milvus record carries chunk_id, chunk_type, reference_month, lsoa_code, crime_type, title, content, dataset_version_id, and the embedding vector. Milvus uses HNSW index with COSINE similarity. Audit events embedding_indexing_started and embedding_indexing_finished are emitted. CLI: `urban-lens-index-embeddings` or `make index-embeddings-latest`.

## Documentation indexing

Architecture and process documents (Markdown files in docs/) are chunked by H2 heading and indexed into Milvus alongside crime evidence. This makes the system's own architecture and training decisions searchable via RAG. Each documentation chunk has chunk_type=documentation, empty reference_month and lsoa_code, and uses the document category as crime_type. CLI: `urban-lens-index-docs` or `make index-docs`.

## ML training

The training job reads forecast_training_set, splits it temporally (last two partitions as holdout, earlier partitions for training), trains three regression candidates (Ridge, RandomForest, ExtraTreesRegressor), evaluates each on the holdout with MAE, RMSE, and MAPE, selects the best, logs all three runs to MLflow, registers the winning model in PostgreSQL model_versions, runs inference on forecast_scoring_set, and publishes forecast_predictions at `gold/ml/forecast_predictions/prediction_month=YYYY-MM/part-000.parquet`. CLI: `urban-lens-train-forecast` or `make train-latest`.

## Governance events timeline

Each pipeline step emits structured audit_events in PostgreSQL. The sequence for a full monthly ingestion is: ingest_started → ingest_finished → transform_started → transform_finished → gold_published → embedding_indexing_started → embedding_indexing_finished → model_training_started → model_training_finished. Every event carries the actor, object_type, object_id, and a details_json payload. Pipeline_run records track start and end timestamps and link input_versions to output_versions.

## Storage path reference

| Layer | Product | Path pattern |
|---|---|---|
| Bronze | Raw CSV | `bronze/data.police.uk/crimes/year=YYYY/month=MM/force=<force>/<file>.csv` |
| Silver | Normalized Parquet | `silver/police_uk/crimes_standardized/year=YYYY/month=MM/part-000.parquet` |
| Gold analytics | Area+month+category | `gold/analytics/crime_metrics_area_month_category/year=YYYY/month=MM/part-000.parquet` |
| Gold analytics | Area+month | `gold/analytics/crime_metrics_area_month/year=YYYY/month=MM/part-000.parquet` |
| Gold analytics | Month+category | `gold/analytics/crime_metrics_month_category/year=YYYY/month=MM/part-000.parquet` |
| Gold RAG | Evidence chunks | `gold/rag/crime_chunks/year=YYYY/month=MM/part-000.parquet` |
| Gold ML | Training set | `gold/ml/forecast_training_set/year=YYYY/month=MM/part-000.parquet` |
| Gold ML | Scoring set | `gold/ml/forecast_scoring_set/year=YYYY/month=MM/part-000.parquet` |
| Gold ML | Predictions | `gold/ml/forecast_predictions/prediction_month=YYYY-MM/part-000.parquet` |

## CLI commands reference

| Command | Makefile target | Purpose |
|---|---|---|
| `urban-lens-ingest` | `make ingest-manual` | Ingest single CSV to Bronze |
| `urban-lens-process-snapshot` | `make process-snapshot` | Ingest all street CSVs in a monthly folder |
| `urban-lens-bronze-to-silver` | `make bronze-to-silver` | Transform one Bronze object to Silver |
| `urban-lens-silver-to-gold` | `make silver-to-gold` | Publish Gold analytics, RAG, and ML datasets |
| `urban-lens-train-forecast` | `make train-latest` | Train and register forecast model |
| `urban-lens-index-embeddings` | `make index-embeddings-latest` | Index crime_chunks into Milvus |
| `urban-lens-index-docs` | `make index-docs` | Index documentation files into Milvus |
