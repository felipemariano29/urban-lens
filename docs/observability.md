# Urban Lens Observability

This document describes the observability stack for Urban Lens.

## Overview

The observability stack consists of:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Promtail**: Log collection from Docker containers

## Quick Start

To start the platform with observability:

```bash
make up-obs    # Start with observability stack only
make up-full   # Start full platform with GPU + observability
```

To view observability logs:

```bash
make logs-obs
```

## URLs

| Service    | URL                        | Default Credentials |
|------------|----------------------------|---------------------|
| Grafana    | http://localhost:3002      | admin / admin       |
| Prometheus | http://localhost:9090      |                     |
| Loki       | http://localhost:3100      |                     |

## Metrics

The API exposes Prometheus metrics at `/metrics`. Key metrics include:

### HTTP Request Metrics

- `urban_lens_http_requests_total` - Total HTTP requests (labels: method, route, status_code, role, plan)
- `urban_lens_http_request_duration_seconds` - Request latency histogram (labels: method, route, role)
- `urban_lens_http_requests_in_progress` - Current in-flight requests (labels: method, route)

### RAG Pipeline Metrics

- `urban_lens_rag_queries_total` - Total RAG queries (labels: query_type, model, status)
- `urban_lens_rag_query_duration_seconds` - RAG query latency (labels: query_type, model)
- `urban_lens_rag_chunks_retrieved` - Chunks retrieved per query (labels: query_type)

### Authentication Metrics

- `urban_lens_api_key_auth_total` - API key authentication attempts (labels: status, plan)
- `urban_lens_rate_limit_hits_total` - Rate limit violations (labels: limit_type, plan)

## Dashboards

The pre-provisioned dashboards include:

### Urban Lens API Overview

Located in Grafana under **Urban Lens** folder.

Panels:

1. **Overview Row**
   - Requests (Last Hour)
   - P95 Latency
   - Rate Limit Hits
   - Error Rate (5xx)

2. **Request Traffic Row**
   - Request Rate by Route
   - Request Rate by Plan

3. **Latency Row**
   - Request Latency Percentiles by Route (p50, p95, p99)

4. **RAG Pipeline Row**
   - RAG Queries by Model
   - RAG Query Latency by Model

5. **Authentication & Quotas Row**
   - API Key Auth Attempts
   - Rate Limit Hits

## Configuration

### Environment Variables

| Variable               | Default | Description              |
|------------------------|---------|--------------------------|
| PROMETHEUS_HOST_PORT   | 9090    | Prometheus web UI port   |
| GRAFANA_HOST_PORT      | 3002    | Grafana web UI port      |
| GRAFANA_ADMIN_USER     | admin   | Grafana admin username   |
| GRAFANA_ADMIN_PASSWORD | admin   | Grafana admin password   |
| LOKI_HOST_PORT         | 3100    | Loki API port            |

### Adding Custom Metrics

To add custom metrics in the API, use the helper functions in `middleware/metrics.py`:

```python
from urban_lens.api.middleware.metrics import record_rag_query, record_rate_limit_hit

# Record RAG query metrics
record_rag_query(
    query_type="chat",
    model="llama3",
    status="success",
    duration_seconds=1.5,
    chunks_count=5
)

# Record rate limit hit
record_rate_limit_hit(limit_type="minute", plan="FREE")
```

## Log Labels

Promtail extracts the following labels from structured logs:

- `level` - Log level (INFO, WARNING, ERROR)
- `request_id` - Correlation ID for request tracing
- `route` - API route path
- `method` - HTTP method
- `status_code` - Response status code
- `model` - LLM model used (for RAG queries)

## Data Retention

- Prometheus: 30 days
- Loki: 30 days

Both can be configured in their respective config files:
- `docker/observability/prometheus.yml`
- `docker/observability/loki-config.yml`

## Troubleshooting

### Grafana shows no data

1. Check that Prometheus is scraping the API:
   - Visit http://localhost:9090/targets
   - Ensure `urban-lens-api` target is UP

2. Verify metrics endpoint is accessible:
   ```bash
   curl http://localhost:8000/metrics
   ```

### Logs not appearing in Loki

1. Check Promtail logs:
   ```bash
   make logs-obs
   ```

2. Ensure Docker socket is accessible by Promtail

3. Verify Loki is receiving data:
   ```bash
   curl http://localhost:3100/ready
   ```
