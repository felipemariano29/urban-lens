# ADR 0001: Segment Gold Products Across RAG, Analytics, and ML

## Status

Accepted

This ADR is part of the completion evidence for `T2` in the governance and medallion delivery plan.

## Context

Urban-Lens must support three distinct workloads on the same public crime data:
- factual answers with evidence-backed retrieval
- structured aggregations for historical and executive analysis
- supervised forecasting for future incident volume

A single shared Gold layer would make schemas unstable and couple unrelated consumers. RAG text chunks, analytical tables, and ML feature sets evolve at different speeds and have different access and quality requirements.

The MVP CSV source contains at least the following fields:
- `Reported by`
- `Falls within`
- `Longitude`
- `Latitude`
- `LSOA code`
- `LSOA name`
- `Crime type`
- `Last outcome category`
- `Context`

Those fields are normalized in Silver and then projected into separate Gold products so the analytics, RAG, and ML consumers do not compete for the same schema.

## Decision

Gold is segmented into three product families:
- `gold/rag`
- `gold/analytics`
- `gold/ml`

The canonical analytical grain is `lsoa_code + reference_month + crime_type`.

The supervised baseline target is `incident_count_next_period`.

Chat runtime uses hybrid routing:
- Gold only for factual questions
- Gold plus model serving for predictive questions
- explicit separation of observed facts and predictions in mixed responses

The design constraints fixed by this ADR are:
- Bronze remains immutable raw evidence.
- Silver remains occurrence-level and non-aggregated.
- Gold Analytics carries structured counts and ratios only.
- Gold RAG carries short evidence snippets only.
- Gold ML carries engineered features, training targets, and scored predictions only.

## Consequences

Positive consequences:
- RAG artifacts can be optimized for embedding without affecting analytics tables
- Analytical datasets can stay stable and explainable
- ML feature datasets can evolve independently while preserving lineage
- Access control can be tuned by Gold product, not only by layer

Trade-offs:
- More Gold datasets to publish and register
- More lineage edges to maintain
- Runtime orchestration needs explicit routing rules

Operational consequences:
- every downstream consumer can choose the narrowest Gold product it needs
- the API can expose evidence payloads without exposing model internals
- the ML pipeline can be retrained independently of RAG chunking changes

## Follow-up

- Expose Gold analytics and model metadata through the FastAPI layer
- Connect Gold RAG chunks to embedding generation and Milvus indexing
- Extend the ML contract later if classification or risk scoring becomes part of the roadmap
- Keep the route for factual answers independent from the route for forecast answers
