CREATE SCHEMA IF NOT EXISTS metadata;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS metadata.datasets (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT        NOT NULL,
    origem      TEXT        NOT NULL,
    descricao   TEXT,
    formato     TEXT        NOT NULL CHECK (formato IN ('csv', 'json', 'parquet', 'geojson', 'other')),
    status      TEXT        NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'deprecated', 'pending')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (nome, origem)
);

CREATE INDEX IF NOT EXISTS idx_datasets_status
    ON metadata.datasets (status);

CREATE INDEX IF NOT EXISTS idx_datasets_origem
    ON metadata.datasets (origem);

CREATE OR REPLACE FUNCTION metadata.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_datasets_updated_at'
    ) THEN
        CREATE TRIGGER trg_datasets_updated_at
        BEFORE UPDATE ON metadata.datasets
        FOR EACH ROW EXECUTE FUNCTION metadata.set_updated_at();
    END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS metadata.load_versions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id  UUID        NOT NULL
                            REFERENCES metadata.datasets (id)
                            ON DELETE CASCADE,
    versao      TEXT        NOT NULL,
    data_carga  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    caminho     TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'running', 'success', 'failed')),
    UNIQUE (dataset_id, versao)
);

CREATE INDEX IF NOT EXISTS idx_load_versions_dataset_id
    ON metadata.load_versions (dataset_id);

CREATE INDEX IF NOT EXISTS idx_load_versions_status
    ON metadata.load_versions (status);

CREATE TABLE IF NOT EXISTS metadata.ingestion_audit (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operacao    TEXT        NOT NULL CHECK (operacao IN (
                                'ingest_started', 'ingest_finished',
                                'validation_failed', 'transform_started',
                                'transform_finished', 'schema_change_detected')),
    resultado   TEXT        NOT NULL CHECK (resultado IN ('ok', 'warning', 'error')),
    detalhes    JSONB       NOT NULL DEFAULT '{}'::jsonb
                            CHECK (jsonb_typeof(detalhes) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_ingestion_audit_timestamp
    ON metadata.ingestion_audit (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_audit_operacao
    ON metadata.ingestion_audit (operacao);

CREATE INDEX IF NOT EXISTS idx_ingestion_audit_detalhes
    ON metadata.ingestion_audit USING GIN (detalhes);

CREATE TABLE IF NOT EXISTS metadata.processed_files (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_arquivo    TEXT        NOT NULL,
    caminho         TEXT        NOT NULL UNIQUE,
    tamanho         BIGINT      NOT NULL CHECK (tamanho >= 0),
    hash            TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'processing',
                                                  'processed', 'failed', 'skipped')),
    processed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_processed_files_status
    ON metadata.processed_files (status);

CREATE INDEX IF NOT EXISTS idx_processed_files_hash
    ON metadata.processed_files (hash);

CREATE TABLE IF NOT EXISTS metadata.response_traceability (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    query           TEXT        NOT NULL,
    chunks_usados   JSONB       NOT NULL DEFAULT '[]'::jsonb
                                CHECK (jsonb_typeof(chunks_usados) = 'array'),
    resposta        TEXT        NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_response_traceability_timestamp
    ON metadata.response_traceability (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_response_traceability_chunks
    ON metadata.response_traceability USING GIN (chunks_usados);


INSERT INTO metadata.datasets (id, nome, origem, descricao, formato, status)
VALUES
    ('a0000000-0000-0000-0000-000000000001',
     'UK Police Street Crime 2023-02',
     'data.police.uk',
     'Street-level crime records for February 2023, all UK forces',
     'csv', 'active'),

    ('a0000000-0000-0000-0000-000000000002',
     'UK Police Stop and Search 2023-02',
     'data.police.uk',
     'Stop-and-search records for February 2023',
     'csv', 'active'),

    ('a0000000-0000-0000-0000-000000000003',
     'UK Police Outcomes 2023-02',
     'data.police.uk',
     'Case outcome records for February 2023',
     'csv', 'active'),

    ('a0000000-0000-0000-0000-000000000004',
     'Urban Lens GeoJSON Boundaries',
     'os.opendata.uk',
     'Police force boundary polygons for spatial joins',
     'geojson', 'active')
ON CONFLICT (nome, origem) DO NOTHING;

INSERT INTO metadata.load_versions (id, dataset_id, versao, data_carga, caminho, status)
VALUES
    ('b0000000-0000-0000-0000-000000000001',
     'a0000000-0000-0000-0000-000000000001',
     '2023-02-v1',
     '2024-01-10 08:00:00+00',
     's3://urban-lens/bronze/street/2023-02/avon-and-somerset-street.csv',
     'success'),

    ('b0000000-0000-0000-0000-000000000002',
     'a0000000-0000-0000-0000-000000000001',
     '2023-02-v2',
     '2024-03-01 09:15:00+00',
     's3://urban-lens/bronze/street/2023-02/avon-and-somerset-street-v2.csv',
     'success'),

    ('b0000000-0000-0000-0000-000000000003',
     'a0000000-0000-0000-0000-000000000002',
     '2023-02-v1',
     '2024-01-10 08:05:00+00',
     's3://urban-lens/bronze/stop-search/2023-02/',
     'success'),

    ('b0000000-0000-0000-0000-000000000004',
     'a0000000-0000-0000-0000-000000000003',
     '2023-02-v1',
     '2024-01-10 08:10:00+00',
     's3://urban-lens/bronze/outcomes/2023-02/',
     'failed'),

    ('b0000000-0000-0000-0000-000000000005',
     'a0000000-0000-0000-0000-000000000004',
     '2024-01-v1',
     '2024-01-15 12:00:00+00',
     's3://urban-lens/bronze/geo/boundaries-2024.geojson',
     'pending')
ON CONFLICT (dataset_id, versao) DO NOTHING;

INSERT INTO metadata.ingestion_audit (id, timestamp, operacao, resultado, detalhes)
VALUES
    ('c0000000-0000-0000-0000-000000000001',
     '2024-01-10 08:00:01+00',
     'ingest_started', 'ok',
     '{"dataset_id": "a0000000-0000-0000-0000-000000000001", "file_count": 43}'::jsonb),

    ('c0000000-0000-0000-0000-000000000002',
     '2024-01-10 08:45:00+00',
     'ingest_finished', 'ok',
     '{"dataset_id": "a0000000-0000-0000-0000-000000000001", "rows_ingested": 128420}'::jsonb),

    ('c0000000-0000-0000-0000-000000000003',
     '2024-01-10 08:10:05+00',
     'validation_failed', 'error',
     '{"dataset_id": "a0000000-0000-0000-0000-000000000003", "reason": "missing outcome_category column", "file": "btp-outcomes.csv"}'::jsonb),

    ('c0000000-0000-0000-0000-000000000004',
     '2024-03-01 09:00:00+00',
     'transform_started', 'ok',
     '{"pipeline": "silver_street_crime", "input_version": "2023-02-v2"}'::jsonb),

    ('c0000000-0000-0000-0000-000000000005',
     '2024-03-01 09:12:00+00',
     'transform_finished', 'ok',
     '{"pipeline": "silver_street_crime", "rows_written": 128420, "duration_sec": 732}'::jsonb)
ON CONFLICT (id) DO NOTHING;

INSERT INTO metadata.processed_files
    (id, nome_arquivo, caminho, tamanho, hash, status, processed_at)
VALUES
    ('d0000000-0000-0000-0000-000000000001',
     '2023-02-avon-and-somerset-street.csv',
     '/data/2023-02/2023-02-avon-and-somerset-street.csv',
     204800, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
     'processed', '2024-01-10 08:30:00+00'),

    ('d0000000-0000-0000-0000-000000000002',
     '2023-02-bedfordshire-street.csv',
     '/data/2023-02/2023-02-bedfordshire-street.csv',
     98304, 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
     'processed', '2024-01-10 08:31:00+00'),

    ('d0000000-0000-0000-0000-000000000003',
     '2023-02-btp-outcomes.csv',
     '/data/2023-02/2023-02-btp-outcomes.csv',
     51200, '6dcd4ce23d88e2ee9568ba546c007c63d9131c1b7b23e12f5ed5b2f8d3c6d8a2',
     'failed', NULL),

    ('d0000000-0000-0000-0000-000000000004',
     '2023-02-cambridgeshire-stop-and-search.csv',
     '/data/2023-02/2023-02-cambridgeshire-stop-and-search.csv',
     30720, 'f4a8b3c2e1d9a7b5c3e2f1a0d8b6c4e2f0a1b3c5e7d9f1b3c5e7d9f1b3c5e7d9',
     'processing', NULL),

    ('d0000000-0000-0000-0000-000000000005',
     'boundaries-2024.geojson',
     '/data/geo/boundaries-2024.geojson',
     2097152, '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
     'pending', NULL)
ON CONFLICT (caminho) DO NOTHING;

INSERT INTO metadata.response_traceability
    (id, query, chunks_usados, resposta, timestamp)
VALUES
    ('e0000000-0000-0000-0000-000000000001',
     'What are the top crime categories in Avon and Somerset in February 2023?',
     '[{"chunk_id": "chunk-001", "source": "silver_street_crime", "score": 0.92},
       {"chunk_id": "chunk-002", "source": "silver_street_crime", "score": 0.88}]'::jsonb,
     'The top crime categories in Avon and Somerset for Feb 2023 were: (1) Violence and sexual offences – 38%, (2) Anti-social behaviour – 22%, (3) Public order – 11%.',
     '2024-04-01 10:05:00+00'),

    ('e0000000-0000-0000-0000-000000000002',
     'How many stop-and-search incidents occurred in Bedfordshire?',
     '[{"chunk_id": "chunk-010", "source": "silver_stop_search", "score": 0.95}]'::jsonb,
     'Bedfordshire recorded 142 stop-and-search incidents in February 2023.',
     '2024-04-01 10:12:00+00'),

    ('e0000000-0000-0000-0000-000000000003',
     'Which force area had the highest number of street crimes?',
     '[{"chunk_id": "chunk-021", "source": "silver_street_crime", "score": 0.97},
       {"chunk_id": "chunk-022", "source": "silver_street_crime", "score": 0.91},
       {"chunk_id": "chunk-023", "source": "silver_street_crime", "score": 0.85}]'::jsonb,
     'Metropolitan Police recorded the highest number of street crimes with 24,312 incidents for February 2023.',
     '2024-04-02 14:00:00+00')
ON CONFLICT (id) DO NOTHING;
