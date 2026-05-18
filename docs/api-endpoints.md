# Urban-Lens API Endpoints

This document summarizes the HTTP endpoints currently exposed by the Urban-Lens API.

## Base URLs

- FastAPI: `http://localhost:${RAG_API_HOST_PORT:-8000}`
- Frontend proxy: `http://localhost:${WEB_HOST_PORT:-3000}/api/v1`

The browser-facing frontend uses Next.js proxy routes under `app/api/v1/*`, but the source-of-truth contract is the FastAPI backend.

## Authentication

The API accepts one of these authentication strategies:

- `Authorization: Bearer <jwt>`
- `X-API-Key: <internal-service-key>`
- `X-API-Key: <governed-api-key>`

JWT roles currently supported:

- `viewer`
- `operator`
- `intel_user`
- `developer`
- `admin`
- `internal_service`

Notes:

- The legacy internal service key maps the caller to the `internal_service` role.
- Governed API keys use the format `ul_<prefix>_<secret>` and are issued by the access endpoint.
- Governed API keys inherit role and plan limits from the stored governance record.
- Governed API keys are also subject to per-minute and per-day quotas derived from the assigned plan or client override.
- If both headers are absent, protected endpoints return `401`.
- Role checks are enforced per endpoint.

### `POST /api/v1/access/credentials`

Purpose:
- Creates or updates a governed user, creates an API client bound to a service plan, and returns a plaintext API key once.

Authentication:
- `admin`, `internal_service`

Request body:

```json
{
  "full_name": "Ana Silva",
  "email": "ana.silva@urbanlens.local",
  "organization": "Urban Lens Security Lab",
  "role": "viewer",
  "plan_code": "FREE",
  "client_name": "grafana-demo",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

Main response fields:
- `user_id`
- `client_id`
- `api_key_id`
- `role`
- `plan_code`
- `client_name`
- `key_prefix`
- `api_key`
- `expires_at`

Typical statuses:
- `201`: credentials issued
- `401`: missing or invalid credentials
- `403`: insufficient role
- `404`: service plan not found

### `GET /api/v1/access/clients`

Purpose:
- Lists API clients with their plan information, rate limits, and active key counts.

Authentication:
- `admin`, `operator`, `internal_service`

Query parameters:
- `user_id`: optional filter by owner user ID
- `include_inactive`: optional boolean to include suspended or revoked clients

Main response fields:
- `clients[]`
- `total`

Each client includes:
- `client_id`
- `user_id`
- `client_name`
- `status`
- `requests_per_minute_override`
- `requests_per_day_override`
- `last_used_at`
- `created_at`
- `user_email`
- `user_full_name`
- `user_role`
- `plan_code`
- `plan_name`
- `plan_requests_per_minute`
- `plan_requests_per_day`
- `active_keys_count`

Typical statuses:
- `200`: clients listed
- `401`: missing or invalid credentials
- `403`: insufficient role
- `502`: governance backend unavailable

### `GET /api/v1/access/keys`

Purpose:
- Lists API keys with their status, usage timestamps, and parent client information.

Authentication:
- `admin`, `operator`, `internal_service`

Query parameters:
- `client_id`: optional filter by parent API client ID
- `include_revoked`: optional boolean to include revoked keys

Main response fields:
- `keys[]`
- `total`

Each key includes:
- `api_key_id`
- `client_id`
- `key_prefix`
- `status`
- `expires_at`
- `issued_at`
- `last_used_at`
- `revoked_at`
- `client_name`
- `user_email`

Typical statuses:
- `200`: keys listed
- `401`: missing or invalid credentials
- `403`: insufficient role
- `502`: governance backend unavailable

### `POST /api/v1/access/keys/{api_key_id}/revoke`

Purpose:
- Permanently revokes an API key. The key cannot be used after revocation.

Authentication:
- `admin`, `operator`, `internal_service`

Path parameters:
- `api_key_id`: the unique API key identifier

Request body (optional):
```json
{
  "reason": "Security incident - key potentially compromised"
}
```

Main response fields:
- `api_key_id`
- `key_prefix`
- `status`
- `revoked_at`
- `message`

Typical statuses:
- `200`: key revoked
- `401`: missing or invalid credentials
- `403`: insufficient role
- `404`: API key not found
- `422`: API key already revoked

### `POST /api/v1/access/keys/{api_key_id}/rotate`

Purpose:
- Rotates an API key by revoking the old key and issuing a new one for the same client.
- The new plaintext key is returned only once.

Authentication:
- `admin`, `operator`, `internal_service`

Path parameters:
- `api_key_id`: the unique API key identifier

Request body (optional):
```json
{
  "expires_at": "2027-06-30T23:59:59Z"
}
```

Main response fields:
- `old_api_key_id`
- `new_api_key_id`
- `client_id`
- `key_prefix`
- `api_key`
- `expires_at`
- `message`

Typical statuses:
- `200`: key rotated, new key returned
- `401`: missing or invalid credentials
- `403`: insufficient role
- `404`: API key not found
- `422`: API key not active or cannot be rotated

### `GET /api/v1/access/me`

Purpose:
- Returns information about the currently authenticated user.

Authentication:
- Any valid authentication (JWT, governed API key, or internal service key)

Main response fields:
- `role`
- `auth_type`
- `user_id` (for governed API keys)
- `client_id` (for governed API keys)
- `api_key_id` (for governed API keys)
- `subject` (for JWT auth)
- `plan_code` (for governed API keys)
- `plan_max_top_k` (for governed API keys)
- `requests_per_minute` (for governed API keys)
- `requests_per_day` (for governed API keys)
- `allowed_models` (for governed API keys)

Typical statuses:
- `200`: current user info returned
- `401`: missing or invalid credentials

### `GET /api/v1/access/me/usage`

Purpose:
- Returns current usage statistics for the authenticated API client.
- Only available for governed API keys.

Authentication:
- Governed API key only

Main response fields:
- `client_id`
- `requests_last_minute`
- `requests_last_day`
- `requests_per_minute_limit`
- `requests_per_day_limit`
- `remaining_minute`
- `remaining_day`

Typical statuses:
- `200`: usage stats returned
- `401`: missing or invalid credentials
- `403`: usage stats only available for governed API keys

## Endpoints

### `GET /api/v1/health`

Purpose:
- Liveness and readiness probe for the API and its core dependencies.

Authentication:
- none

Main response fields:
- `status`
- `version`
- `timestamp`
- `dependencies.catalog`
- `dependencies.rag_embedder`
- `dependencies.rag_vector_store`

Typical statuses:
- `200`: all dependencies healthy
- `207`: API online, but one or more dependencies unavailable

### `GET /api/v1/system/models`

Purpose:
- Returns the local Ollama model catalog used by the frontend model selector.

Authentication:
- `viewer`, `operator`, `intel_user`, `developer`, `admin`, `internal_service`

Main response fields:
- `default_chat_model`
- `default_embedding_model`
- `models[]`

Each item in `models[]` may include:
- `name`
- `size_bytes`
- `digest`
- `modified_at`

Typical statuses:
- `200`: model catalog returned
- `401`: missing or invalid credentials
- `502`: Ollama unavailable

### `POST /api/v1/query`

Purpose:
- Executes semantic similarity search over indexed crime evidence chunks.

Authentication:
- `viewer`, `operator`, `admin`, `internal_service`

Request body:

```json
{
  "query": "burglary in Westminster January 2024",
  "top_k": 5,
  "filters": {
    "crime_type": "Burglary",
    "lsoa_code": "E01001234",
    "reference_month": "2024-01"
  }
}
```

Plan behaviour:
- Governed API keys may be blocked when `top_k` exceeds the maximum allowed by the caller plan.
- Governed API keys may also receive `429` when the request quota for the current minute or day is exhausted.

Response shape:
- `results[]`

Each result includes:
- `id`
- `score`
- `content`
- `metadata.chunk_type`
- `metadata.reference_month`
- `metadata.lsoa_code`
- `metadata.crime_type`
- `metadata.title`
- `metadata.dataset_version_id`

Typical statuses:
- `200`: ranked evidence returned
- `401`: missing or invalid credentials
- `403`: plan or role restriction violated
- `429`: governed plan quota exhausted
- `502`: RAG backend unavailable

### `POST /api/v1/chat/query`

Purpose:
- Runs the complete governed RAG pipeline with retrieval, evidence assembly, and Ollama generation.

Authentication:
- `viewer`, `operator`, `intel_user`, `developer`, `admin`, `internal_service`

Request body:

```json
{
  "query": "Quais evidencias sustentam aumento de burglary em Westminster em 2024-01?",
  "top_k": 5,
  "model": "llama3",
  "filters": {
    "lsoa_code": "E01001234",
    "reference_month": "2024-01",
    "crime_type": "burglary"
  }
}
```

Notes:

- `model` is optional. When omitted, the API uses `URBAN_LENS_CHAT_MODEL`.
- `filters.chunk_type` is only honored for `developer` and `admin`.
- Governed API keys may be restricted to a subset of Ollama models according to the assigned service plan.
- Governed API keys may also have a lower `top_k` cap than the global request schema allows.
- Governed API keys may receive `429` when the request quota for the current minute or day is exhausted.

Response shape:
- `answer`
- `evidences[]`
- `context[]`
- `profile`
- `fallback_reason`
- `timings_ms`

Important response details:
- `answer.status` is either `answered` or `insufficient_evidence`
- `answer.model` shows which Ollama model generated the answer
- `timings_ms` returns `embedding_ms`, `retrieval_ms`, `generation_ms`, and `total_ms`

Typical statuses:
- `200`: generated answer or fallback with evidence payload
- `401`: missing or invalid credentials
- `403`: authenticated caller lacks permission
- `429`: governed plan quota exhausted
- `502`: RAG backend unavailable

### `GET /api/v1/metadata`

Purpose:
- Lists dataset catalog entries registered in Urban-Lens governance metadata.

Authentication:
- `viewer`, `operator`, `admin`, `internal_service`

Query parameters:
- `source`: optional logical dataset name filter

Role-based visibility:
- `viewer`: `logical_name`, `layer`
- `operator`: adds `version`
- `admin` and `internal_service`: adds `id`, `object_path`, `created_at`

Typical statuses:
- `200`: catalog entries returned
- `401`: missing or invalid credentials
- `403`: insufficient role
- `502`: catalog backend unavailable

### `GET /api/v1/metadata/runs`

Purpose:
- Lists MLflow training runs and selected metadata for the forecast pipeline.

Authentication:
- `admin`, `internal_service`

Query parameters:
- `experiment_name`
- `dataset_version`
- `start_date`
- `end_date`

Main response fields per run:
- `run_id`
- `experiment_id`
- `experiment_name`
- `run_name`
- `status`
- `start_time`
- `end_time`
- `artifact_uri`
- `metrics.mae`
- `metrics.rmse`
- `metrics.mape`
- `params`
- `dataset_version`

Typical statuses:
- `200`: runs returned
- `403`: insufficient role
- `404`: experiment not found
- `422`: invalid date range

### `GET /internal/status`

Purpose:
- Internal-only status endpoint.

Authentication:
- `admin`, `internal_service`

Notes:

- `include_in_schema=False`, so it does not appear in Swagger.

Typical response:

```json
{
  "status": "ok",
  "role": "internal_service"
}
```

## Swagger

The API exposes interactive Swagger/OpenAPI documentation through the FastAPI app when the service is running.

Recommended use:

- use Swagger for live request testing
- use this Markdown file as the quick operational summary
