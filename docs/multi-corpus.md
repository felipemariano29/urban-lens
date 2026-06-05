# Multi-Corpus Retrieval Architecture

This document describes the multi-corpus retrieval architecture in Urban Lens.

## Overview

Urban Lens uses two separate Milvus collections to store different types of knowledge:

| Collection | Purpose | Content |
|------------|---------|---------|
| `crime_chunks` | Crime data from DATA.POLICE.UK | Area summaries, crime type distributions, temporal patterns |
| `knowledge_chunks` | Platform knowledge | MLflow run summaries, documentation, configuration |

## Query Routing

The RAG pipeline automatically routes queries to the appropriate corpus based on intent detection.

### Intent Detection

The `detect_query_intent()` function classifies queries into categories:

| Intent | Trigger Phrases | Corpus |
|--------|-----------------|--------|
| `platform_knowledge` | "mlflow", "urban lens", "architecture", "how does it work" | knowledge |
| `crime_type_listing` | "what crime types", "quais tipos de crime" | crime |
| `dominant_crime` | "most common crime", "crime dominante" | crime |
| `comparison` | "compare", "versus", "vs" | crime |
| `generic` | (default) | hybrid |

### Corpus Selection

```python
from urban_lens.rag.query_understanding import intent_to_corpus

corpus = intent_to_corpus(intent)
# Returns: "crime", "knowledge", or "hybrid"
```

## Collection Schemas

### crime_chunks

```
chunk_id        VARCHAR(64)   PRIMARY KEY
chunk_type      VARCHAR(32)   # "area_summary", "temporal", "comparison"
reference_month VARCHAR(7)    # "2024-01"
lsoa_code       VARCHAR(16)   # "E01000001"
crime_type      VARCHAR(64)   # "Burglary", "Violence and sexual offences"
title           VARCHAR(512)
content         VARCHAR(65535)
dataset_version_id VARCHAR(36)
embedding       FLOAT_VECTOR(768)
```

### knowledge_chunks

```
chunk_id        VARCHAR(64)   PRIMARY KEY
chunk_type      VARCHAR(32)   # "mlflow_run", "doc_section", "config"
source_type     VARCHAR(32)   # "mlflow", "docs", "api"
title           VARCHAR(512)
content         VARCHAR(65535)
run_id          VARCHAR(64)   # MLflow run ID (nullable)
experiment_id   VARCHAR(64)   # MLflow experiment ID (nullable)
embedding       FLOAT_VECTOR(768)
```

## Usage

### Searching crime data

```python
from urban_lens.infrastructure.vector_store import MilvusVectorStore

store = MilvusVectorStore(uri="http://localhost:19530")
hits = store.search(
    query_embedding=embedding,
    top_k=5,
    filters={"lsoa_code": "E01000001", "reference_month": "2024-01"}
)
```

### Searching platform knowledge

```python
hits = store.search_knowledge(
    query_embedding=embedding,
    top_k=5,
    filters={"source_type": "mlflow"}
)
```

### Hybrid search

```python
hits = store.search_multi(
    query_embedding=embedding,
    collections=["crime", "knowledge"],
    top_k=5,
    crime_filters={"lsoa_code": "E01000001"},
    knowledge_filters={"source_type": "mlflow"}
)
```

## Indexing Knowledge

### MLflow Run Summaries

MLflow runs can be indexed into the knowledge corpus:

```python
from urban_lens.infrastructure.vector_store import MilvusVectorStore
from urban_lens.infrastructure.embedder import OllamaEmbedder

embedder = OllamaEmbedder("http://localhost:11434", "nomic-embed-text")
store = MilvusVectorStore("http://localhost:19530")

# Create knowledge collection
store.ensure_knowledge_collection()

# Index MLflow run
record = {
    "chunk_id": f"mlflow_run_{run_id}",
    "chunk_type": "mlflow_run",
    "source_type": "mlflow",
    "title": f"Forecast Model Run {run_id}",
    "content": f"Experiment: {experiment_name}\nMetrics: MAE={mae}, RMSE={rmse}\nParams: {params}",
    "run_id": run_id,
    "experiment_id": experiment_id,
    "embedding": embedder.embed([content])[0],
}
store.upsert_knowledge_chunks([record])
```

### Documentation Sections

Platform documentation can also be indexed:

```python
record = {
    "chunk_id": "doc_api_overview",
    "chunk_type": "doc_section",
    "source_type": "docs",
    "title": "API Overview",
    "content": "The Urban Lens API provides...",
    "run_id": "",
    "experiment_id": "",
    "embedding": embedder.embed(["The Urban Lens API provides..."])[0],
}
store.upsert_knowledge_chunks([record])
```

## Pipeline Integration

The RAG pipeline automatically selects the corpus:

```python
from urban_lens.rag.pipeline import RagPipeline
from urban_lens.rag.contracts import RagQuery

pipeline = RagPipeline(config)

# This query goes to knowledge_chunks
response = pipeline.run(RagQuery(
    query="How does the Urban Lens forecasting model work?",
    ...
))

# This query goes to crime_chunks
response = pipeline.run(RagQuery(
    query="What crimes were reported in E01000001 in January 2024?",
    ...
))

# This query searches both corpora
response = pipeline.run(RagQuery(
    query="Tell me about recent trends",
    ...
))
```

## Extending

To add a new corpus type:

1. Add collection constants in `vector_store.py`
2. Add `ensure_<name>_collection()` method
3. Add `upsert_<name>_chunks()` method
4. Add `search_<name>()` method
5. Add new intent in `query_understanding.py`
6. Update `intent_to_corpus()` mapping
7. Update `search_multi()` to include new collection
