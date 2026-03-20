# Governance and Medallion Delivery Plan

## Status

This document is the execution plan for the Urban-Lens governance and medallion backlog. It translates the approved architecture into delivery tasks that can be assigned to multiple agents or engineers.

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and `OPTIONAL` are to be interpreted as described in RFC 2119.

Task status:
- `T1` completed on 2026-03-20 through `docs/architecture/metadata-contract.md`
- `T2` completed on 2026-03-20 through the medallion architecture and ADR documents
- `T3` completed on 2026-03-20 through `sql/init/001_governance_schema.sql`
- `T4` completed on 2026-03-20 through pure transformations and tests using real `DATA.POLICE.UK` January snapshot files
- `T5` completed on 2026-03-20 through job orchestration, snapshot ingestion support, and end-to-end tests with fake infrastructure
- `T6` to `T8` remain available for execution and delegation

## Delivery Goal

The delivery MUST finish with all of the following in place:
- a complete governance contract for metadata, lineage, audit, and access
- a documented medallion architecture for Bronze, Silver, and Gold
- a working Bronze to Silver to Gold pipeline
- Gold products for RAG, analytics, and ML
- a baseline supervised model workflow for future incident-count prediction
- enough documentation for other team members to operate, validate, and extend the solution

## Delivery Waves

The work SHALL be executed in waves because some tasks are true blockers and some are parallelizable.

### Wave 0: Foundation Lock

This wave MUST complete first because every downstream task depends on it.

Tasks:
- `T1` Governance contract and final delivery boundaries

### Wave 1: Independent Foundation Work

These tasks MAY run in parallel after `T1` is approved.

Tasks:
- `T2` Medallion documentation and architectural decisions
- `T3` PostgreSQL governance schema and access policy definitions
- `T4` Pure transformation contract for Bronze, Silver, Gold, and ML features

### Wave 2: Pipeline Integration

These tasks MAY run in parallel after their direct dependencies from Wave 1 are complete.

Tasks:
- `T5` Pipeline orchestration and metadata registration
- `T6` Gold RAG output and chat routing contract

### Wave 3: Model and Operational Closure

These tasks MAY run in parallel after Wave 2 produces stable Gold datasets.

Tasks:
- `T7` ML baseline training and prediction publication
- `T8` Runbook, validation, and final acceptance evidence

## Task Definitions

### `T1` Governance Contract and Scope Lock

Status:
- Completed

Primary scope:
- `RAG-266`

Purpose:
- establish the single source of truth for governance objects and response evidence

Required outputs:
- `docs/architecture/metadata-contract.md`
- confirmed response contract for factual and predictive answers
- confirmed list of event types, profiles, and minimum metadata fields

Mandatory requirements:
- The task MUST define `dataset_versions`, `pipeline_runs`, `lineage_edges`, `audit_events`, `access_policies`, and `model_versions`.
- The task MUST define which metadata fields are required, optional, and consumer-facing.
- The task MUST define the minimum evidence payload for RAG and API responses.
- The task MUST define how predictions are disclosed and MUST state that predictions SHALL NOT be presented as observed facts.
- The task MUST define the MVP profiles `admin`, `analyst`, `manager`, and `operator`.

Out of scope:
- writing executable pipeline code
- provisioning infrastructure

Definition of done:
- all downstream teams can implement against the same contract without creating new fields by assumption
- the document resolves the ownership boundary between Gold analytics, Gold RAG, and Gold ML

Parallelization:
- This task SHALL NOT be parallelized with other contract-writing tasks that change the same governance definitions.
- This task MAY be reviewed in parallel by backend, data, and ML owners after the initial draft exists.

### `T2` Medallion Documentation and ADRs

Primary scope:
- `RAG-229`
- `RAG-231`

Purpose:
- document the layer behavior, path conventions, quality rules, and design rationale

Required outputs:
- `docs/architecture/medallion-governance.md`
- `docs/adr/0001-medallion-layout.md`

Mandatory requirements:
- The task MUST define path patterns for Bronze, Silver, and each Gold product family.
- The task MUST define the canonical grain for Silver, Gold analytics, and Gold ML.
- The task MUST define quality gates by layer.
- The task MUST explain why Gold is segmented across RAG, analytics, and ML.
- The task MUST define the hybrid chat-routing policy at the architecture level.

Out of scope:
- PostgreSQL DDL
- executable orchestration code

Definition of done:
- an implementer can derive file layout, partitioning, and allowed data movement from the documentation alone

Parallelization:
- This task MAY run in parallel with `T3` and `T4`.
- This task SHOULD be owned by a documentation-focused agent because it writes shared design truth and should avoid code churn.

### `T3` PostgreSQL Governance Schema

Primary scope:
- `RAG-266`

Purpose:
- translate the governance contract into executable relational structures

Required outputs:
- `sql/init/001_governance_schema.sql`

Mandatory requirements:
- The task MUST create the `governance` schema.
- The task MUST create tables for dataset versions, pipeline runs, lineage edges, audit events, access policies, and model versions.
- The task MUST encode minimal integrity checks such as valid layer values and non-negative row counts.
- The task MUST seed the default access profiles required by the governance contract.
- The task SHOULD keep the schema compatible with monthly dataset publication and ML model registration.

Out of scope:
- API endpoints
- pipeline transformation logic

Definition of done:
- a fresh PostgreSQL instance can apply the SQL without manual edits
- the resulting schema can store every artifact produced by the medallion pipeline and the forecast workflow

Parallelization:
- This task MAY run in parallel with `T2` and `T4`.
- This task SHOULD own only `sql/` and database-facing contract details.
- Other agents MUST NOT modify the same SQL files while this task is in progress.

### `T4` Transformation Contract for Bronze, Silver, Gold, and ML

Status:
- Completed

Primary scope:
- `RAG-229`
- `RAG-230`

Purpose:
- implement the pure business logic that converts CSV rows into governed analytical products

Required outputs:
- `src/urban_lens/pipeline/transformations.py`
- unit tests for normalization, aggregation, and feature generation

Mandatory requirements:
- The task MUST normalize incoming CSV columns from `DATA.POLICE.UK`.
- The task MUST infer `reference_month` from the CSV or source path when needed.
- The task MUST compute a stable `record_hash`.
- The task MUST produce Gold analytics views for:
  - area and month and category
  - area and month
  - month and category
- The task MUST produce RAG evidence records from Gold outputs.
- The task MUST produce ML training and scoring datasets with the official target `incident_count_next_period`.
- The task MUST use temporal logic for lag and moving-average features.

Out of scope:
- storage I/O
- metadata registration
- model fitting

Definition of done:
- all pure transformations are testable without MinIO, PostgreSQL, or MLflow
- tests prove that specific, aggregated, and future-target outputs are generated correctly

Parallelization:
- This task MAY run in parallel with `T2` and `T3`.
- This task SHOULD own only pure transformation code and related tests.
- Other agents MUST NOT edit orchestration or SQL files under this task’s ownership.

### `T5` Pipeline Orchestration and Metadata Registration

Status:
- Completed

Primary scope:
- `RAG-230`

Purpose:
- connect storage, metadata registration, lineage, audit, and transformation steps into runnable jobs

Required outputs:
- `src/urban_lens/pipeline/jobs.py`
- CLI entrypoints in `pipelines/`
- storage and metadata adapters

Mandatory requirements:
- The task MUST ingest a local CSV into Bronze and register the Bronze dataset version.
- The task MUST transform Bronze to Silver and register lineage from Bronze to Silver.
- The task MUST transform Silver to Gold and register lineage for every Gold product.
- The task MUST emit audit events for ingestion, transformation, and publication milestones.
- The task SHOULD keep job boundaries aligned with the medallion layers.

Out of scope:
- model architecture design
- frontend or API integration

Definition of done:
- an operator can execute the jobs in order and obtain Bronze, Silver, and Gold artifacts plus governance metadata

Parallelization:
- This task SHALL wait for `T3` and `T4`.
- After those are stable, this task MAY run in parallel with `T6`.
- This task SHOULD own `src/urban_lens/pipeline/jobs.py`, `src/urban_lens/storage.py`, `src/urban_lens/metadata.py`, and `pipelines/`.

### `T6` Gold RAG Output and Chat Routing Contract

Primary scope:
- `RAG-266`
- downstream dependency for RAG and API teams

Purpose:
- ensure the chat layer can decide between factual retrieval and predictive serving without ambiguity

Required outputs:
- query-intent classification rules
- factual and predictive response contract implementation helpers
- tests for routing behavior

Mandatory requirements:
- The task MUST classify questions as factual, predictive, or mixed.
- The task MUST route factual questions to Gold-only retrieval.
- The task MUST route predictive questions to Gold context plus model serving.
- The task MUST preserve explicit separation between observed facts and model predictions.
- The task SHOULD remain heuristic and lightweight for the MVP unless a stronger classifier is explicitly required.

Out of scope:
- LLM prompt implementation
- Milvus integration

Definition of done:
- an API or chat implementer can consume the routing result and produce transparent factual or predictive responses

Parallelization:
- This task MAY run in parallel with `T5` once `T1` and `T2` are stable.
- This task SHOULD own only routing and contract helpers, not transformation or SQL files.

### `T7` ML Baseline Training and Prediction Publication

Primary scope:
- `RAG-230`
- future alignment with MLflow work

Purpose:
- train the baseline regressor, evaluate it on a temporal holdout, and publish predictions back into governed storage

Required outputs:
- `src/urban_lens/ml.py`
- prediction publication path and model-version registration

Mandatory requirements:
- The task MUST train a regression baseline for `incident_count_next_period`.
- The task MUST split train and holdout temporally, never randomly.
- The task MUST log metrics to MLflow.
- The task MUST register model metadata in PostgreSQL.
- The task MUST publish forecast outputs as a governed Gold artifact.
- The task SHOULD use a model that is tabular, explainable enough for the MVP, and easy to retrain locally.

Out of scope:
- benchmark matrix for many models
- classification or risk scoring

Definition of done:
- the project can train once, produce metrics, and publish predictions with full lineage to the training and scoring datasets

Parallelization:
- This task SHALL wait for `T5`.
- This task MAY run in parallel with `T8`.
- This task SHOULD own only ML training, scoring, and related metadata registration files.

### `T8` Runbook, Validation, and Final Acceptance Evidence

Primary scope:
- `RAG-231`
- operational closure for `RAG-230`

Purpose:
- ensure the implemented solution is understandable and repeatable by the team

Required outputs:
- `docs/implementation-guide.md`
- `.env.example`
- final validation checklist

Mandatory requirements:
- The task MUST explain the execution order of the jobs.
- The task MUST define required services and variables.
- The task MUST document how to validate successful Bronze, Silver, Gold, and ML outputs.
- The task SHOULD include a minimal smoke-test procedure for a sample CSV.

Out of scope:
- architecture redesign
- new pipeline features

Definition of done:
- another engineer can set up the environment and execute the documented flow without relying on tribal knowledge

Parallelization:
- This task MAY start early in draft form, but it SHALL finish only after `T5` and `T7` stabilize.
- This task SHOULD own operational documentation only.

## Parallelization Matrix

| Task | Depends on | Can run in parallel with | Recommended owner profile | Recommended file ownership |
| --- | --- | --- | --- | --- |
| `T1` | None | Review-only parallelism | Governance lead | `docs/architecture/metadata-contract.md` |
| `T2` | `T1` | `T3`, `T4` | Documentation or architecture agent | `docs/architecture/`, `docs/adr/` |
| `T3` | `T1` | `T2`, `T4` | Database or backend agent | `sql/` |
| `T4` | `T1` | `T2`, `T3` | Data engineering agent | `src/urban_lens/pipeline/transformations.py`, `tests/test_transformations.py` |
| `T5` | `T3`, `T4` | `T6` | Data platform agent | `src/urban_lens/pipeline/jobs.py`, `src/urban_lens/storage.py`, `src/urban_lens/metadata.py`, `pipelines/` |
| `T6` | `T1`, `T2` | `T5` | Backend or RAG agent | `src/urban_lens/query_routing.py`, routing tests |
| `T7` | `T5` | `T8` | ML agent | `src/urban_lens/ml.py` |
| `T8` | `T5`, `T7` for finalization | Drafting may overlap earlier tasks | Enablement or documentation agent | `docs/implementation-guide.md`, `.env.example` |

## Recommended Multi-Agent Execution Strategy

Recommended assignment:
- Agent A SHALL own `T1`.
- Agent B SHALL own `T2`.
- Agent C SHALL own `T3`.
- Agent D SHALL own `T4`.
- Agent E SHALL own `T5`.
- Agent F SHALL own `T6`.
- Agent G SHALL own `T7`.
- Agent H MAY own `T8`.

Recommended execution order:
1. Agent A locks `T1`.
2. Agents B, C, and D execute `T2`, `T3`, and `T4` in parallel.
3. Agent E starts `T5` after C and D finish.
4. Agent F executes `T6` once A and B are stable.
5. Agent G executes `T7` after E publishes stable Gold ML datasets.
6. Agent H closes `T8` after E and G stabilize the runnable flow.

Coordination rules:
- Each agent MUST treat its file ownership as exclusive unless re-coordination happens first.
- Agents MUST NOT revert work from other agents.
- Shared contracts in `docs/architecture/` SHALL be considered source-of-truth documents.
- If `T1` changes after Wave 1 starts, downstream tasks MUST be revalidated before merge.

## Acceptance Checklist

The full delivery SHALL be accepted only if all of the following are true:
- governance metadata can represent every dataset and model artifact produced by the pipeline
- Bronze, Silver, and Gold outputs follow documented path and quality rules
- Gold provides products for analytics, RAG, and ML
- the baseline model can train on Gold ML outputs and publish predictions
- factual and predictive responses have explicit disclosure rules
- tests validate the critical transformation and routing behaviors
- operational documentation explains how another team member can run the flow
