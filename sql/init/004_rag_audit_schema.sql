CREATE TABLE IF NOT EXISTS governance.retrieval_events (
    retrieval_event_id UUID PRIMARY KEY,
    audit_id UUID NOT NULL,
    query TEXT NOT NULL,
    query_intent TEXT NOT NULL CHECK (query_intent IN ('factual', 'temporal_comparison', 'trend_forecast')),
    retrieval_method TEXT NOT NULL CHECK (retrieval_method IN ('milvus_semantic', 'postgres_structured', 'hybrid')),
    chunks_requested INT NOT NULL CHECK (chunks_requested >= 0),
    chunks_returned INT NOT NULL CHECK (chunks_returned >= 0),
    min_score DOUBLE PRECISION NOT NULL CHECK (min_score >= 0 AND min_score <= 1),
    max_score DOUBLE PRECISION NOT NULL CHECK (max_score >= 0 AND max_score <= 1),
    mean_score DOUBLE PRECISION NOT NULL CHECK (mean_score >= 0 AND mean_score <= 1),
    retrieval_latency_ms INT NOT NULL CHECK (retrieval_latency_ms >= 0),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL CHECK (status IN ('success', 'low_confidence', 'failed'))
);

CREATE TABLE IF NOT EXISTS governance.chunk_retrieval_audit (
    chunk_audit_id UUID PRIMARY KEY,
    retrieval_event_id UUID NOT NULL REFERENCES governance.retrieval_events (retrieval_event_id) ON DELETE CASCADE,
    chunk_id TEXT NOT NULL,
    dataset_version_id UUID NOT NULL REFERENCES governance.dataset_versions (id),
    rank INT NOT NULL CHECK (rank > 0),
    relevance_score DOUBLE PRECISION NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 1),
    crime_type TEXT NOT NULL,
    reference_month TEXT NOT NULL CHECK (reference_month ~ '^[0-9]{4}-[0-9]{2}$'),
    included_in_response BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_retrieval_events_timestamp
    ON governance.retrieval_events (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_chunk_retrieval_audit_retrieval_event_id
    ON governance.chunk_retrieval_audit (retrieval_event_id);

CREATE INDEX IF NOT EXISTS idx_chunk_retrieval_audit_chunk_dataset
    ON governance.chunk_retrieval_audit (chunk_id, dataset_version_id);
