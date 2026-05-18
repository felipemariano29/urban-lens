# Urban Lens - Technical Roadmap for Next Phase

## Purpose

This document consolidates the next implementation phase for Urban Lens into a single technical roadmap.

Goals:

- absorb the existing Sprint 9 MLflow plan into a broader execution roadmap
- standardize repository structure and runtime conventions
- improve security, traceability, and operational governance
- make the platform easier to run, evolve, and observe
- prepare the project for a more production-like architecture without overengineering it

This roadmap should be read together with:

- `docs/sprint-9-execution-plan.md`
- `docs/implementation-guide.md`
- `docs/how-to-run.md`
- `docs/architecture/medallion-governance.md`
- `docs/architecture/metadata-contract.md`

## Executive Summary

The current backend package under `src/urban_lens` is already a reasonable modular monolith, but the repository has grown organically around it. The main issues are not in the core RAG flow itself, but in the boundaries between frontend, backend, Docker runtime, governance, and operational tooling.

The highest priority corrections are:

1. stop using a single internal API key as the effective identity for browser traffic
2. containerize the frontend and standardize Docker startup and health checks
3. separate technical knowledge retrieval from crime evidence retrieval
4. expand governance to include user identity, API keys, plans, quotas, and request audit
5. extend Sprint 9 so MLflow runs and platform knowledge also become queryable context
6. finish the monorepo migration by removing stale root-level frontend artifacts and legacy scripts

## Current Architecture Diagnosis

### What is already good

- Python code is mostly organized by domain under `src/urban_lens`
- FastAPI routers, workflows, RAG pipeline, governance store, and infrastructure adapters are separated
- the Medallion model is already reflected in documentation and pipeline outputs
- MLflow, MinIO, PostgreSQL, Milvus, and Ollama are already provisioned locally

### What is currently confusing or poorly organized

#### Repository root mixes too many concerns

Today the root contains Next.js app files, Python package files, Docker files, docs, test assets, data snapshots, and compatibility wrappers all at the same level.

Impact:

- navigation is harder than necessary
- ownership boundaries are unclear
- runtime concerns and source code concerns are mixed
- stale root-level frontend folders create false entrypoints and should not coexist with `apps/web`
- demo and OS-specific helper scripts are easier to maintain under `scripts/`, not in the repository root

#### Frontend is not part of the Docker stack

The backend stack runs in Compose, but the frontend still starts separately via `make frontend`.

Impact:

- environment drift between developers
- harder demos and onboarding
- inconsistent logs and health visibility

#### Compose startup relies on simple `depends_on` and sleep-based setup

`minio-setup` and `ollama-setup` use inline shell entrypoints with fixed wait times.

Impact:

- brittle startup order
- flaky cold starts
- difficult troubleshooting

#### Authentication model is not compatible with request-level governance

The backend supports JWT and API key, but the current Next.js proxy can inject the internal API key on proxied requests. That makes user-level attribution unreliable for browser traffic.

Impact:

- loss of true caller identity
- poor auditability
- impossible to enforce FREE/PRO quotas correctly

#### Vector storage naming no longer matches usage

The current Milvus collection is named `crime_chunks`, but documentation chunks are also indexed into it.

Impact:

- naming is misleading
- future self-knowledge retrieval gets harder to reason about
- platform and domain corpora are coupled too early

#### Governance schema tracks data and pipelines, but not API consumers

The current governance tables cover dataset versions, pipeline runs, lineage, audit events, access policies, and model versions.

Missing:

- users
- API clients
- API keys
- request audit
- quotas and plan limits
- request/usage analytics

#### Documentation drift exists

There are signs of contract drift across runtime docs, ports, and behavior. Some files also show encoding issues.

Impact:

- confusion during setup
- increased maintenance cost
- weaker trust in documentation as source of truth

## Recommended Target Structure

Urban Lens should remain a modular monolith, but the repository should move toward an apps-and-infra layout.

Suggested target:

```text
urban-lens/
  apps/
    api/
      src/urban_lens/
      tests/
      pyproject.toml
    web/
      app/
      components/
      hooks/
      lib/
      public/
      package.json
  infra/
    compose/
      compose.yml
      compose.gpu.yml
      compose.observability.yml
    docker/
      api/
      web/
      mlflow/
      scripts/
  sql/
    init/
    migrations/
  scripts/
    dev/
    ops/
  docs/
    architecture/
    adr/
  data/
```

### Boundary rules

- `apps/api` owns FastAPI, workflows, governance logic, and RAG services
- `apps/web` owns UI, route handlers, and browser-side interactions
- `infra/compose` owns environment assembly
- `infra/docker` owns container images and entrypoint scripts
- `scripts` owns operational helpers, not business logic
- `sql/migrations` should become the source of schema evolution after bootstrap

## Architecture Decisions for the Next Phase

### Keep a modular monolith

Do not split Urban Lens into microservices yet. The current scale does not justify it.

Use internal modules for:

- query API
- governance and identity
- RAG retrieval and generation
- experiment tracking integration
- observability

### Separate corpora logically

The platform should distinguish between:

- domain evidence corpus: crime and public safety data
- platform knowledge corpus: documentation, architecture, governance, MLflow summaries, prompt variants, evaluation summaries

Suggested options:

1. two Milvus collections: `crime_chunks` and `knowledge_chunks`
2. one generic collection name plus a required `corpus_kind` field

Preferred choice:

- two collections for clarity and easier troubleshooting

### Keep `/health` simple

Do not overload `/api/v1/health` with model catalogs or other dynamic inventory. Keep it for readiness and dependency status.

Add a dedicated endpoint such as:

- `GET /api/v1/system/models`

This endpoint should return available Ollama models and the configured default model.

### Return execution metadata intentionally

The chat contract should return operationally useful metadata, but not dump raw internal metadata to all users.

Recommended public response additions:

- `timings.embedding_ms`
- `timings.retrieval_ms`
- `timings.generation_ms`
- `timings.total_ms`
- `collections_used`
- `chunk_types_used`
- `dataset_versions_used`
- `model`

Technical fields should remain role-filtered.

## Roadmap by Epic

## Epic 0 - Repository and Runtime Standardization

### Objective

Make the project easier to navigate and operate before adding more features.

### Scope

- move toward `apps/api` and `apps/web`
- relocate Dockerfiles into `infra/docker`
- relocate Compose files into `infra/compose`
- keep compatibility wrappers only temporarily
- normalize environment variable names and defaults
- remove stale root-level frontend duplicates after migration
- keep only the environment files required by actual runtime modes
- fix documentation drift and encoding problems

### Main files impacted

- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker/api/Dockerfile`
- `docker/mlflow/Dockerfile`
- `Makefile`
- `README.md`
- `docs/how-to-run.md`
- `docs/implementation-guide.md`

### Acceptance criteria

- a new engineer can identify where API, web, infra, docs, and scripts live in under five minutes
- startup docs and actual ports/services match
- there is no competing frontend tree outside `apps/web`
- local development requires only `.env`; extra `.env.*` files exist only for explicit alternate runtimes

## Epic 1 - Docker Completion and Health Checks

### Objective

Run the full platform, including the frontend, through Docker Compose with deterministic startup.

### Scope

- add a frontend Docker image
- add frontend service to Compose
- add health checks to all long-running containers
- replace inline shell entrypoints with `.sh` scripts
- use `depends_on.condition` where supported by the chosen Compose path
- keep one CPU-first base compose and one GPU overlay

### Suggested health checks

- Postgres: `pg_isready`
- MinIO: `/minio/health/live`
- MLflow: HTTP GET on the tracking server
- Milvus: readiness endpoint or client-level probe wrapper
- Ollama: API probe
- rag-api: `GET /api/v1/health`
- frontend: HTTP GET on the root page or internal health route

### Main files impacted

- `docker-compose.yml`
- `docker-compose.prod.yml`
- `Makefile`
- new `infra/docker/web/Dockerfile`
- new `infra/docker/scripts/*.sh`

### Acceptance criteria

- one command can start the full local platform
- the platform no longer relies on arbitrary `sleep` values for readiness

## Epic 2 - Makefile and Developer Operations

### Objective

Standardize common workflows for startup, teardown, logs, and runtime profile selection.

### Scope

- detect CPU vs GPU compose path automatically or via explicit target
- create grouped log commands
- keep the default path simple for local use

### Recommended targets

- `make up`
- `make up-cpu`
- `make up-gpu`
- `make down`
- `make reset`
- `make ps`
- `make urls`
- `make logs-core`
- `make logs-app`
- `make logs-obs`
- `make logs-all`

### Notes

If automatic GPU detection becomes unreliable across environments, prefer explicit targets over opaque detection.

### Acceptance criteria

- developers do not need to comment or uncomment GPU blocks manually
- logs for the main services are easy to follow

## Epic 3 - Identity, API Keys, Plans, and Request Governance

### Objective

Introduce real caller identity, traceability, and usage controls suitable for a security-oriented platform.

### Scope

- add user and API consumer entities
- add generated API keys with secure storage
- add FREE and PRO plans
- add per-key and per-user quota enforcement
- add request audit and request metrics
- stop treating all browser traffic as `internal_service`

### Recommended schema additions

- `governance.users`
- `governance.api_clients`
- `governance.api_keys`
- `governance.subscription_plans`
- `governance.plan_limits`
- `governance.request_audit`
- `governance.usage_counters`

### Authentication redesign

- browser users should authenticate as themselves
- service-to-service traffic may still use machine API keys
- the internal API key should not become the effective end-user identity

### Recommended API additions

- `POST /api/v1/access/keys`
- `POST /api/v1/access/keys/rotate`
- `POST /api/v1/access/keys/revoke`
- `GET /api/v1/access/me`

### Acceptance criteria

- every protected request can be attributed to a real user or real client identity
- FREE and PRO limits are enforced from persisted data

## Epic 4 - Chat Contract and User-Facing Runtime Metadata

### Objective

Improve the chat API contract and remove confusing response fields.

### Scope

- remove the public return of the loosely-defined "additional metadata"
- return backend-measured timings
- return model used
- return collections and dataset versions used
- expose available models through a dedicated endpoint

### Recommended chat response evolution

- `answer`
- `evidences`
- `profile`
- `fallback_reason`
- `timings`
- `retrieval`
- `model`

Where:

- `timings` contains phase timing breakdown
- `retrieval` contains `collections_used`, `chunk_types_used`, `dataset_versions_used`, `top_k`

### Main files impacted

- `src/urban_lens/api/models/response.py`
- `src/urban_lens/rag/contracts.py`
- `src/urban_lens/api/services/rag_service.py`
- `src/urban_lens/rag/pipeline.py`
- `hooks/use-urban-lens.ts`
- `lib/types.ts`
- `components/urban-lens/*`

### Acceptance criteria

- the frontend shows the backend-reported total inference time
- the response contract is explicit and easier to document

## Epic 5 - Ollama Model Catalog and Selection

### Objective

Allow multiple local LLMs and let the user select the model from the frontend safely.

### Scope

- bootstrap around five local models
- return available models from the backend
- persist a configured default model
- validate requested models server-side
- expose model selector in the frontend

### Recommended endpoint

- `GET /api/v1/system/models`

Suggested payload:

- `default_model`
- `embedding_model`
- `available_generation_models`
- `available_embedding_models`

### Acceptance criteria

- the frontend can switch model per request
- invalid model names are rejected explicitly

## Epic 6 - Sprint 9 Plus MLflow Knowledge Integration

### Objective

Absorb Sprint 9 into the next platform phase and go beyond "MLflow exists" to "MLflow supports iteration and self-knowledge".

### This epic includes the existing Sprint 9 plan

The current detailed source of truth remains:

- `docs/sprint-9-execution-plan.md`

This roadmap expands it with two additional goals:

1. experiment metadata should remain inspectable via API for operators
2. experiment summaries should also become retrievable knowledge for the RAG layer

### Scope from Sprint 9

- fixed evaluation dataset
- prompt variants
- RAG evaluation runner
- MLflow logging of params, metrics, and artifacts
- experiment comparison workflow
- reproducible runbook

### Additional scope for this roadmap

- generate normalized summary documents for MLflow runs
- index those summaries into the technical knowledge corpus
- make runs queryable in natural language
- allow questions about model comparisons, metrics, preprocessing, and prompt versions

### Recommended implementation pieces

- `evaluation/rag/*`
- `src/urban_lens/workflows/rag_evaluation.py`
- `src/urban_lens/cli/evaluate_rag.py`
- `src/urban_lens/workflows/mlflow_knowledge_indexing.py`
- `src/urban_lens/api/routers/system.py`

### Recommended indexed knowledge sources

- architecture docs
- governance docs
- medallion documentation
- prompt variants and evaluation summaries
- MLflow run summaries
- model training summaries

### Acceptance criteria

- at least two prompt variants are comparable in MLflow
- run summaries are available both in MLflow UI and via knowledge retrieval
- the chat can answer how the platform was vectorized and how Bronze, Silver, and Gold are used

## Epic 7 - Knowledge Retrieval Architecture

### Objective

Teach the model to answer questions about the platform itself without weakening the crime-focused retrieval path.

### Scope

- split crime evidence retrieval from technical knowledge retrieval
- classify question intent before retrieval
- support hybrid retrieval when necessary

### Question classes

- crime analysis
- platform/process explanation
- experiment/model comparison
- hybrid questions

### Retrieval strategy

- crime questions query `crime_chunks`
- platform questions query `knowledge_chunks`
- hybrid questions query both and merge with clear provenance

### Acceptance criteria

- the chat can explain embeddings, bucket layering, and document indexing behavior
- crime answers and platform answers remain distinguishable and grounded

## Epic 8 - Observability with Grafana

### Objective

Visualize request behavior, user activity, errors, latency, and model usage.

### Scope

- add Prometheus, Grafana, Loki, Tempo, and collector/agent layer
- instrument FastAPI with request metrics and traces
- emit structured logs
- dashboard requests by user, plan, route, model, and status code

### Recommended telemetry fields

- `request_id`
- `user_id`
- `api_key_id`
- `plan`
- `route`
- `method`
- `status_code`
- `model`
- `collections_used`
- `latency_ms`
- `fallback_reason`

### Dashboard set

- API overview
- user activity
- model usage
- latency and failures
- quota consumption

### Acceptance criteria

- Grafana can answer who requested what, when, with which model, and how long it took

## Suggested Execution Order

1. Epic 0 - Repository and Runtime Standardization
2. Epic 1 - Docker Completion and Health Checks
3. Epic 2 - Makefile and Developer Operations
4. Epic 3 - Identity, API Keys, Plans, and Request Governance
5. Epic 4 - Chat Contract and User-Facing Runtime Metadata
6. Epic 5 - Ollama Model Catalog and Selection
7. Epic 6 - Sprint 9 Plus MLflow Knowledge Integration
8. Epic 7 - Knowledge Retrieval Architecture
9. Epic 8 - Observability with Grafana

## Dependency Notes

- Epic 3 should start before exposing FREE/PRO plans publicly
- Epic 4 depends on Epic 3 if response metadata must include authenticated user identity or plan
- Epic 5 can start in parallel with Epic 4 after the system endpoint contract is agreed
- Epic 6 can begin in parallel with Epic 5, but full self-knowledge indexing should wait for Epic 7 design decisions
- Epic 8 should start early for log foundations, but final dashboards depend on Epic 3 and Epic 4 fields

## Backlog Starter

Suggested initial backlog items:

- `ARCH-300` Define target repository structure and migration path
- `OPS-301` Containerize Next.js frontend
- `OPS-302` Add health checks to all Compose services
- `OPS-303` Replace inline Compose entrypoints with shell scripts
- `OPS-304` Add CPU/GPU Compose strategy to Makefile
- `OPS-305` Add grouped log targets to Makefile
- `SEC-310` Design users, API clients, API keys, and plans schema
- `SEC-311` Implement API key issuance and secure storage
- `SEC-312` Implement request audit trail and quota enforcement
- `API-320` Add `/api/v1/system/models`
- `API-321` Return inference timings and retrieval usage metadata
- `API-322` Remove ambiguous additional metadata from public response
- `RAG-330` Split crime corpus and knowledge corpus
- `RAG-331` Index architecture and governance docs into knowledge corpus
- `RAG-332` Index MLflow run summaries into knowledge corpus
- `MLF-340` Implement Sprint 9 evaluation dataset and runner
- `MLF-341` Log RAG evaluation runs and artifacts in MLflow
- `OBS-350` Add Grafana, Prometheus, Loki, and Tempo stack
- `OBS-351` Add request metrics, traces, and structured logs

## Risks and Mitigations

### Risk: architecture refactor stalls feature delivery

Mitigation:

- keep Epic 0 focused on structure and compatibility, not rewrites
- migrate by boundary, not all at once

### Risk: governance becomes too heavy for the current maturity level

Mitigation:

- start with PostgreSQL-backed request audit and quota counters
- avoid introducing a dedicated gateway product too early

### Risk: self-knowledge retrieval pollutes crime answers

Mitigation:

- separate corpora
- classify intent before retrieval
- expose provenance in the response

### Risk: model selection creates unstable UX

Mitigation:

- whitelist supported models server-side
- expose default and available models via backend, not hardcoded frontend lists

### Risk: observability labels explode in cardinality

Mitigation:

- keep high-cardinality fields in log payloads or traces
- use a restrained metrics label set

## Definition of Done for the Next Phase

The next phase should be considered complete only when all of the following are true:

- the full platform, including frontend, runs in Docker
- all major services expose health checks
- CPU and GPU startup paths are explicit and documented
- browser and API traffic can be attributed to real users or clients
- FREE and PRO plans are enforceable
- the chat returns model and inference timing information
- the backend exposes a proper model catalog endpoint
- Sprint 9 RAG evaluation runs are reproducible in MLflow
- MLflow and platform knowledge can be queried through the RAG layer
- Grafana can show request activity by user, route, model, and plan

## Immediate Recommendation

If execution needs to start now, begin with this slice:

1. Epic 1
2. Epic 2
3. Epic 3 schema design
4. Epic 4 response contract update
5. Epic 6 Sprint 9 evaluation runner

That sequence reduces operational fragility first, then fixes governance, then unlocks the higher-value product capabilities.
