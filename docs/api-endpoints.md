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

JWT roles currently supported:

- `viewer`
- `operator`
- `intel_user`
- `developer`
- `admin`
- `internal_service`

Notes:

- `X-API-Key` maps the caller to the `internal_service` role.
- If both headers are absent, protected endpoints return `401`.
- Role checks are enforced per endpoint.

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

Response shape:
- `answer`
- `evidences[]`
- `context[]`
- `profile`
- `fallback_reason`

Important response details:
- `answer.status` is either `answered` or `insufficient_evidence`
- `answer.model` shows which Ollama model generated the answer

Typical statuses:
- `200`: generated answer or fallback with evidence payload
- `401`: missing or invalid credentials
- `403`: authenticated caller lacks permission
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
