CREATE TABLE IF NOT EXISTS governance.service_plans (
    id UUID PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    requests_per_minute INTEGER NOT NULL CHECK (requests_per_minute > 0),
    requests_per_day INTEGER NOT NULL CHECK (requests_per_day > 0),
    max_top_k INTEGER NOT NULL DEFAULT 5 CHECK (max_top_k BETWEEN 1 AND 20),
    allowed_models JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(allowed_models) = 'array'),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata_json) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS governance.users (
    id UUID PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    organization TEXT,
    role TEXT NOT NULL CHECK (role IN ('viewer', 'operator', 'intel_user', 'developer', 'admin')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS governance.api_clients (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES governance.users (id),
    plan_id UUID NOT NULL REFERENCES governance.service_plans (id),
    client_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    requests_per_minute_override INTEGER CHECK (requests_per_minute_override IS NULL OR requests_per_minute_override > 0),
    requests_per_day_override INTEGER CHECK (requests_per_day_override IS NULL OR requests_per_day_override > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    UNIQUE (user_id, client_name)
);

CREATE TABLE IF NOT EXISTS governance.api_keys (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES governance.api_clients (id),
    key_prefix TEXT NOT NULL UNIQUE,
    key_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired')),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata_json) = 'object')
);

CREATE TABLE IF NOT EXISTS governance.request_audit (
    id UUID PRIMARY KEY,
    request_id TEXT NOT NULL,
    user_id UUID REFERENCES governance.users (id),
    client_id UUID REFERENCES governance.api_clients (id),
    api_key_id UUID REFERENCES governance.api_keys (id),
    plan_id UUID REFERENCES governance.service_plans (id),
    route_path TEXT NOT NULL,
    http_method TEXT NOT NULL,
    response_status INTEGER,
    model_name TEXT,
    latency_ms DOUBLE PRECISION CHECK (latency_ms IS NULL OR latency_ms >= 0),
    remote_ip TEXT,
    user_agent TEXT,
    filters_json JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(filters_json) = 'object'),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata_json) = 'object'),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_governance_users_status
    ON governance.users (status);

CREATE INDEX IF NOT EXISTS idx_governance_api_clients_user_id
    ON governance.api_clients (user_id);

CREATE INDEX IF NOT EXISTS idx_governance_api_clients_status
    ON governance.api_clients (status);

CREATE INDEX IF NOT EXISTS idx_governance_api_keys_client_id
    ON governance.api_keys (client_id);

CREATE INDEX IF NOT EXISTS idx_governance_api_keys_status
    ON governance.api_keys (status);

CREATE INDEX IF NOT EXISTS idx_governance_request_audit_requested_at
    ON governance.request_audit (requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_governance_request_audit_user_id_requested_at
    ON governance.request_audit (user_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_governance_request_audit_route_requested_at
    ON governance.request_audit (route_path, requested_at DESC);

INSERT INTO governance.service_plans (
    id,
    code,
    name,
    description,
    requests_per_minute,
    requests_per_day,
    max_top_k,
    allowed_models,
    metadata_json
)
VALUES
    (
        '10000000-0000-0000-0000-000000000001',
        'FREE',
        'Free',
        'Entry tier for basic governed access to the Urban-Lens API.',
        10,
        500,
        5,
        '["llama3","phi3"]'::jsonb,
        '{"priority": "low"}'::jsonb
    ),
    (
        '10000000-0000-0000-0000-000000000002',
        'PRO',
        'Pro',
        'Higher-throughput tier for operational and analytical users.',
        60,
        5000,
        10,
        '["llama3","mistral","qwen2.5","phi3"]'::jsonb,
        '{"priority": "normal"}'::jsonb
    )
ON CONFLICT (code) DO NOTHING;
