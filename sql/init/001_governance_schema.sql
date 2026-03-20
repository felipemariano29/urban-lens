CREATE SCHEMA IF NOT EXISTS governance;

CREATE TABLE IF NOT EXISTS governance.dataset_versions (
    id UUID PRIMARY KEY,
    source_name TEXT NOT NULL,
    layer TEXT NOT NULL CHECK (layer IN ('bronze', 'silver', 'gold')),
    logical_name TEXT NOT NULL,
    version TEXT NOT NULL CHECK (version ~ '^[0-9]{4}-[0-9]{2}$'),
    schema_version TEXT NOT NULL,
    object_path TEXT NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    content_hash TEXT NOT NULL,
    valid_from TEXT NOT NULL CHECK (valid_from ~ '^[0-9]{4}-[0-9]{2}$'),
    valid_to TEXT CHECK (valid_to IS NULL OR valid_to ~ '^[0-9]{4}-[0-9]{2}$'),
    status TEXT NOT NULL DEFAULT 'available',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valid_to IS NULL OR valid_to >= valid_from),
    UNIQUE (layer, logical_name, version, object_path)
);

CREATE TABLE IF NOT EXISTS governance.pipeline_runs (
    id UUID PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    run_type TEXT NOT NULL CHECK (run_type IN ('manual', 'scheduled', 'ad_hoc')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    triggered_by TEXT NOT NULL,
    input_versions JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(input_versions) = 'array'),
    output_versions JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(output_versions) = 'array'),
    error_summary TEXT
);

CREATE TABLE IF NOT EXISTS governance.lineage_edges (
    id UUID PRIMARY KEY,
    upstream_dataset_version_id UUID NOT NULL REFERENCES governance.dataset_versions (id),
    downstream_dataset_version_id UUID NOT NULL REFERENCES governance.dataset_versions (id),
    transformation_name TEXT NOT NULL,
    pipeline_run_id UUID NOT NULL REFERENCES governance.pipeline_runs (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (upstream_dataset_version_id, downstream_dataset_version_id, transformation_name)
);

CREATE TABLE IF NOT EXISTS governance.audit_events (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'ingest_started',
        'ingest_finished',
        'validation_failed',
        'transform_started',
        'transform_finished',
        'gold_published',
        'model_training_started',
        'model_training_finished',
        'model_inference_requested',
        'model_inference_completed'
    )),
    actor TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    object_type TEXT NOT NULL CHECK (object_type IN ('dataset_version', 'pipeline_run', 'lineage_edge', 'model_version')),
    object_id TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details_json) = 'object')
);

CREATE TABLE IF NOT EXISTS governance.access_policies (
    id UUID PRIMARY KEY,
    profile_name TEXT NOT NULL,
    layer_scope TEXT NOT NULL CHECK (layer_scope IN ('bronze', 'silver', 'gold', '*')),
    dataset_scope TEXT NOT NULL,
    allowed_actions JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(allowed_actions) = 'array'),
    metadata_visibility JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata_visibility) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (profile_name, layer_scope, dataset_scope)
);

CREATE TABLE IF NOT EXISTS governance.model_versions (
    id UUID PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    target_name TEXT NOT NULL,
    training_dataset_version_id UUID NOT NULL REFERENCES governance.dataset_versions (id),
    scoring_dataset_version_id UUID NOT NULL REFERENCES governance.dataset_versions (id),
    training_window_start TEXT NOT NULL CHECK (training_window_start ~ '^[0-9]{4}-[0-9]{2}$'),
    training_window_end TEXT NOT NULL CHECK (training_window_end ~ '^[0-9]{4}-[0-9]{2}$'),
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metrics_json) = 'object'),
    artifact_uri TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (training_window_end >= training_window_start),
    UNIQUE (model_name, model_version)
);

INSERT INTO governance.access_policies (id, profile_name, layer_scope, dataset_scope, allowed_actions, metadata_visibility)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'admin', 'bronze', '*', '["read","write","publish","audit"]'::jsonb, '{"dataset_version": true, "pipeline_run": true, "model_version": true}'::jsonb),
    ('00000000-0000-0000-0000-000000000002', 'admin', 'silver', '*', '["read","write","publish","audit"]'::jsonb, '{"dataset_version": true, "pipeline_run": true, "model_version": true}'::jsonb),
    ('00000000-0000-0000-0000-000000000003', 'admin', 'gold', '*', '["read","write","publish","audit"]'::jsonb, '{"dataset_version": true, "pipeline_run": true, "model_version": true}'::jsonb),
    ('00000000-0000-0000-0000-000000000004', 'analyst', 'gold', '*', '["read"]'::jsonb, '{"dataset_version": true, "pipeline_run": false, "model_version": true}'::jsonb),
    ('00000000-0000-0000-0000-000000000005', 'manager', 'gold', 'crime_metrics_area_month', '["read"]'::jsonb, '{"dataset_version": true, "pipeline_run": false, "model_version": false}'::jsonb),
    ('00000000-0000-0000-0000-000000000006', 'operator', 'gold', 'crime_metrics_area_month_category', '["read"]'::jsonb, '{"dataset_version": true, "pipeline_run": false, "model_version": false}'::jsonb)
ON CONFLICT (profile_name, layer_scope, dataset_scope) DO NOTHING;
