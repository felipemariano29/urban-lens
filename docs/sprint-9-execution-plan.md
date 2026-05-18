# Sprint 9 Execution Plan

## Scope

This plan covers the implementation of Sprint 9 from the course presentation:

- MLflow and evaluation
- experiment tracking
- prompt comparison
- quality metrics for the RAG system

Sprint 9 expected outcome from the course scope:

- experiments registered

This plan is written against the current repository state after AC2 closure through Sprint 8.

## Current Baseline

The repository already has the following foundations in place:

- MLflow is provisioned in [docker-compose.yml](../docker-compose.yml)
- baseline forecasting runs are logged to MLflow in [src/urban_lens/forecasting/training.py](../src/urban_lens/forecasting/training.py)
- forecast publication and model registration already exist in [src/urban_lens/workflows/forecast.py](../src/urban_lens/workflows/forecast.py)
- the RAG pipeline is implemented and documented in [docs/rag-end-to-end.md](rag-end-to-end.md)
- prompt construction is centralized in [src/urban_lens/rag/generation.py](../src/urban_lens/rag/generation.py)
- RAG API paths already exist in [src/urban_lens/api/routers/query.py](../src/urban_lens/api/routers/query.py)
- MLflow metadata exposure already exists for forecast runs in [src/urban_lens/api/routers/metadata.py](../src/urban_lens/api/routers/metadata.py)

Conclusion:

- Sprint 9 should not rebuild MLflow from scratch
- Sprint 9 should extend the current platform so that RAG experiments are tracked and comparable in a governed way

## Sprint 9 Goal

Implement a reproducible RAG evaluation layer that:

- registers prompt and evaluation experiments in MLflow
- compares prompt variants against a fixed evaluation set
- logs relevance and retrieval quality metrics
- produces evidence that the RAG system can be iterated systematically

## Deliverables

At the end of Sprint 9, the repository should contain:

- a documented evaluation strategy for RAG
- a lightweight evaluation dataset for prompt and retrieval comparison
- a CLI or workflow to run RAG evaluations locally
- MLflow runs for RAG evaluation experiments
- comparable prompt variants with clear version identifiers
- metrics that support ranking and regression detection
- operational instructions for rerunning the evaluation

## Out of Scope

The following are not required to close Sprint 9:

- replacing the current local LLM stack
- building an online human feedback system
- implementing a full annotation platform
- integrating predictive-answer UX into the frontend
- redesigning the main governance schema unless a small additive field is clearly justified

## Definition of Done

Sprint 9 is complete only if all of the following are true:

- at least two prompt variants can be evaluated against the same dataset
- each evaluation run is registered in MLflow
- evaluation metrics are logged in a way that supports comparison
- the project can identify which prompt variant performed better on the chosen benchmark
- another engineer can reproduce the evaluation flow using repository documentation

## Recommended Architecture

Sprint 9 should extend the current architecture with a dedicated RAG evaluation flow:

1. fixed evaluation dataset
2. prompt variant selection
3. automated execution through the existing RAG pipeline
4. metric computation
5. MLflow logging
6. optional API exposure for experiment inspection

Recommended MLflow organization:

- keep forecast training under the existing experiment family
- create a dedicated experiment for RAG evaluation, for example:
  - `urban-lens-rag-eval`

Recommended prompt versioning model:

- `prompt_family`: identifies the prompt use case, for example `factual_rag`
- `prompt_version`: identifies the prompt variant, for example `v1`, `v2`, `v3`
- `prompt_language_strategy`: for example `auto`, `pt`, `en`
- `context_budget_strategy`: fixed or capped retrieval context variant

## Work Packages

### WP1 - Evaluation Contract Lock

Objective:

- define exactly what will be measured and how

Implementation:

- create a new document, recommended name:
  - `docs/rag-evaluation.md`
- define the evaluation set schema
- define the accepted prompt comparison dimensions
- define the metrics and tie-breaking rules

Minimum dataset schema:

- `id`
- `question`
- `filters`
- `expected_answer_keywords`
- `expected_citations_min`
- `expected_status`
- `notes`

Recommended metric set:

- `answer_rate`
- `fallback_rate`
- `retrieval_hit_rate_at_k`
- `citation_count_avg`
- `citation_coverage_rate`
- `keyword_match_rate`
- `latency_ms_avg`

Recommended metric meanings:

- `answer_rate`: percentage of cases with `answer.status = answered`
- `fallback_rate`: percentage of cases that return insufficient evidence
- `retrieval_hit_rate_at_k`: percentage of cases where at least one retrieved chunk matches the expected target pattern
- `citation_count_avg`: average number of returned evidences
- `citation_coverage_rate`: percentage of cases meeting the minimum evidence expectation
- `keyword_match_rate`: percentage of cases where expected answer keywords appear in the generated answer
- `latency_ms_avg`: average response latency

Acceptance:

- the repository has one source-of-truth document for RAG evaluation

### WP2 - Lightweight Evaluation Dataset

Objective:

- create a deterministic local benchmark

Implementation:

- create a small JSON or JSONL dataset under a new folder, recommended:
  - `evaluation/rag/`
- include 10 to 20 benchmark questions
- prefer stable questions grounded in the lightweight demo datasets
- include both:
  - straightforward retrieval questions
  - synthesis questions with evidence expectations

Recommended files:

- `evaluation/rag/factual_eval_set.json`
- optional future file:
  - `evaluation/rag/prompt_comparison_notes.md`

Question design rules:

- avoid ambiguous or open-ended questions
- use periods already available in the repository, such as `2026-01`
- avoid requiring external labels or human-only interpretation

Acceptance:

- the benchmark can be executed locally without new infrastructure

### WP3 - Prompt Variant Support

Objective:

- make prompt comparison explicit and reproducible

Implementation:

- refactor the current prompt builder in [src/urban_lens/rag/generation.py](../src/urban_lens/rag/generation.py)
- add prompt variant selection without breaking the current default
- recommended function shape:
  - `build_prompt(..., prompt_version="v1")`
- implement at least two prompt variants:
  - `v1`: current prompt behavior
  - `v2`: revised instruction strategy

Recommended changes:

- keep `v1` behavior identical to current production behavior
- isolate variant-specific instructions in small helper functions
- log the chosen prompt version during evaluation

Acceptance:

- two prompt variants can be selected deterministically

### WP4 - RAG Evaluation Runner

Objective:

- automate evaluation runs end to end

Implementation:

- create a new workflow or CLI, recommended files:
  - `src/urban_lens/workflows/rag_evaluation.py`
  - `src/urban_lens/cli/evaluate_rag.py`
- the runner should:
  - load the evaluation dataset
  - execute the RAG flow for each sample
  - collect outputs
  - compute aggregate metrics
  - log everything to MLflow

Recommended CLI contract:

```bash
python -m urban_lens.cli.evaluate_rag \
  --dataset-path evaluation/rag/factual_eval_set.json \
  --prompt-version v1 \
  --model llama3 \
  --top-k 5 \
  --experiment-name urban-lens-rag-eval \
  --actor sprint-9
```

What to log to MLflow:

- params:
  - `prompt_family`
  - `prompt_version`
  - `model`
  - `top_k`
  - `dataset_path`
  - `dataset_size`
  - `evaluation_type`
- metrics:
  - `answer_rate`
  - `fallback_rate`
  - `retrieval_hit_rate_at_k`
  - `citation_count_avg`
  - `citation_coverage_rate`
  - `keyword_match_rate`
  - `latency_ms_avg`
- artifacts:
  - raw per-question results as JSON
  - aggregate summary as JSON or Markdown

Recommended artifact paths:

- `results/per_question.json`
- `results/summary.json`

Acceptance:

- one command creates a comparable RAG evaluation run in MLflow

### WP5 - Experiment Comparison and Metadata Exposure

Objective:

- make experiment comparison visible and inspectable

Implementation:

- reuse or extend [src/urban_lens/api/routers/metadata.py](../src/urban_lens/api/routers/metadata.py)
- support listing RAG evaluation runs by experiment name
- optionally add filtering by:
  - `prompt_version`
  - `evaluation_type`

Recommended approach:

- do not create a new API unless required
- first extend the current metadata listing to surface RAG evaluation runs clearly
- use MLflow params as filters where possible

Acceptance:

- an operator can inspect forecast runs and RAG evaluation runs through documented APIs or MLflow UI

### WP6 - Documentation and Runbook Closure

Objective:

- make Sprint 9 reproducible

Implementation:

- update:
  - `docs/implementation-guide.md`
  - `docs/how-to-run.md`
  - `README.md`
- add:
  - `docs/rag-evaluation.md`
- document:
  - how to run the evaluation benchmark
  - how to compare prompt variants in MLflow
  - what metrics matter
  - how to interpret regressions

Acceptance:

- another engineer can rerun the benchmark and compare variants without tribal knowledge

## File Plan

Recommended new files:

- `docs/sprint-9-execution-plan.md`
- `docs/rag-evaluation.md`
- `evaluation/rag/factual_eval_set.json`
- `src/urban_lens/workflows/rag_evaluation.py`
- `src/urban_lens/cli/evaluate_rag.py`
- optional:
  - `tests/test_rag_evaluation.py`

Recommended updates:

- `src/urban_lens/rag/generation.py`
- `src/urban_lens/rag/pipeline.py`
- `src/urban_lens/api/routers/metadata.py`
- `docs/implementation-guide.md`
- `docs/how-to-run.md`
- `README.md`

## Metrics Specification

### Minimum required metrics

- `answer_rate`
- `fallback_rate`
- `keyword_match_rate`
- `latency_ms_avg`

### Strongly recommended metrics

- `retrieval_hit_rate_at_k`
- `citation_coverage_rate`
- `citation_count_avg`

### Optional future metrics

- answer length distribution
- duplicate citation ratio
- unsupported-claim proxy
- prompt token proxy if token accounting is later added

## Validation Strategy

### Local validation

Run:

1. ingest a lightweight demo dataset
2. index embeddings
3. confirm Milvus contents
4. execute the evaluation runner with `prompt_version=v1`
5. execute the evaluation runner with `prompt_version=v2`
6. compare both runs in MLflow

### Success conditions

- both runs appear in MLflow
- both runs log the agreed metrics
- raw result artifacts are available
- prompt versions are visible in params
- one prompt can be identified as better or at least observably different

### Regression checks

- prompt refactor must not break existing `/api/v1/chat/query`
- current `demo_rag.py` must continue to work
- existing RAG tests must still pass

## Suggested Sprint Backlog

1. `RAG-280` Define RAG evaluation contract and benchmark metrics
2. `RAG-281` Create lightweight factual evaluation dataset
3. `RAG-282` Add prompt version support to the RAG generator
4. `RAG-283` Implement RAG evaluation workflow and CLI
5. `RAG-284` Log RAG evaluation experiments in MLflow
6. `RAG-285` Expose or document experiment comparison flow
7. `RAG-286` Update runbook and documentation for Sprint 9

## Recommended Execution Order

1. Lock the evaluation contract and metrics
2. Build the benchmark dataset
3. Add prompt versioning
4. Implement the evaluation runner
5. Log experiments into MLflow
6. Expose comparison and update docs

## Risks and Mitigations

### Risk: evaluation metrics are too subjective

Mitigation:

- use lightweight deterministic proxy metrics first
- avoid starting with LLM-as-a-judge in Sprint 9

### Risk: benchmark questions are weak or unstable

Mitigation:

- ground them in the `demo-yyyy-mm` datasets already used in the repository
- prefer factual questions with clear expectations

### Risk: prompt comparison becomes noisy

Mitigation:

- fix the dataset
- fix the model
- fix `top_k`
- compare one variable at a time

### Risk: MLflow becomes overloaded with mixed run types

Mitigation:

- use a dedicated RAG evaluation experiment name
- include clear params such as `evaluation_type` and `prompt_version`

## Acceptance Checklist

Sprint 9 should be accepted only if:

- MLflow contains reproducible RAG evaluation runs
- at least two prompt variants are comparable
- the benchmark dataset is versioned inside the repository
- aggregate quality metrics are documented
- the runbook explains how to rerun and interpret the experiments

## Final Output Expected from Sprint 9

By the end of Sprint 9, the project should be able to say:

- forecast experiments are tracked in MLflow
- RAG prompt experiments are also tracked in MLflow
- prompt variants can be compared using a local benchmark
- evaluation metrics are documented and reproducible

That is the point where Sprint 9 is not just "MLflow exists", but "MLflow supports real iteration on model and prompt quality".
