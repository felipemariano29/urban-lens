# Metadata Contract

## Purpose

This contract defines the minimum governance objects that must exist for Urban-Lens to support traceable RAG responses, auditable medallion datasets, and forecast-model training.

The contract is intentionally shared across data engineering, backend, RAG, and ML so the same metadata identifiers can be used end-to-end.

Related relational documentation:
- [Metadata relational model](metadata-relational-model.md)

## Status

This document is the completion artifact for `T1` in the governance and medallion delivery plan.

`T1` SHALL be considered complete only if:
- all governance entities are defined
- required versus optional versus consumer-facing fields are explicit
- factual and predictive response contracts are explicit
- access profiles and disclosure rules are explicit

## Contract Rules

- All downstream implementation teams MUST treat this document as the source of truth for governance metadata.
- Teams MUST NOT invent new required fields for the entities below without updating this contract first.
- Fields marked as consumer-facing MAY appear in API and chat payloads.
- Fields not marked as consumer-facing SHALL remain internal unless another contract explicitly exposes them.

## Governance Entities

### `dataset_versions`

Represents a concrete published artifact in Bronze, Silver, or Gold.

Required fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable identifier used in lineage and API evidence payloads |
| `source_name` | Public source or system that originated the artifact |
| `layer` | `bronze`, `silver`, or `gold` |
| `logical_name` | Stable dataset name independent of the storage path |
| `version` | Human-readable partition or release version, monthly for the MVP |
| `schema_version` | Version of the artifact schema |
| `object_path` | MinIO object key for the concrete artifact |
| `row_count` | Reconciliation and audit metric |
| `content_hash` | Integrity check for the artifact payload |
| `valid_from` | First period covered by the dataset |
| `valid_to` | Last period covered by the dataset when applicable |
| `status` | Publication state |
| `metadata_json` | Additional governance attributes such as force, run id, and product |

Optional fields:
- `valid_to` for open-ended monthly publications

Consumer-facing fields:
- `id`
- `source_name`
- `layer`
- `logical_name`
- `version`
- `valid_from`
- `valid_to`
- `status`

### `pipeline_runs`

Represents one execution of a medallion or ML job.

Required fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable run identifier |
| `pipeline_name` | Job name such as `ingest_manual` or `silver_to_gold` |
| `run_type` | `manual`, `scheduled`, or another controlled value |
| `started_at` / `finished_at` | Execution timestamps |
| `status` | Running, completed, or failed |
| `triggered_by` | Human or system actor |
| `input_versions` | Upstream dataset version identifiers |
| `output_versions` | Downstream dataset version identifiers |
| `error_summary` | Failure context when relevant |

Optional fields:
- `finished_at` while the run is still active
- `error_summary` for successful runs

Consumer-facing fields:
- none by default

Operational-facing fields:
- `id`
- `pipeline_name`
- `run_type`
- `started_at`
- `finished_at`
- `status`
- `triggered_by`
- `input_versions`
- `output_versions`
- `error_summary`

### `lineage_edges`

Represents lineage between upstream and downstream datasets.

Required fields:

| Field | Purpose |
| --- | --- |
| `upstream_dataset_version_id` | Input dataset |
| `downstream_dataset_version_id` | Output dataset |
| `transformation_name` | Controlled transformation label |
| `pipeline_run_id` | Execution that produced the lineage relation |

Optional fields:
- none

Consumer-facing fields:
- none by default

Operational-facing fields:
- `upstream_dataset_version_id`
- `downstream_dataset_version_id`
- `transformation_name`
- `pipeline_run_id`

### `audit_events`

Represents operational and governance events.

Minimum event types:
- `ingest_started`
- `ingest_finished`
- `validation_failed`
- `transform_started`
- `transform_finished`
- `gold_published`
- `model_training_started`
- `model_training_finished`
- `model_inference_requested`
- `model_inference_completed`
- `embedding_indexing_started`
- `embedding_indexing_finished`

Required fields:
- `id`
- `event_type`
- `actor`
- `timestamp`
- `object_type`
- `object_id`
- `details_json`

Optional fields:
- none

Consumer-facing fields:
- none by default

### `access_policies`

Represents visibility and action rules by profile.

Profiles defined for the MVP:
- `admin`
- `analyst`
- `manager`
- `operator`

Required fields:
- `profile_name`
- `layer_scope`
- `dataset_scope`
- `allowed_actions`
- `metadata_visibility`

Optional fields:
- none

Consumer-facing fields:
- `profile_name`
- `allowed_actions`

### `model_versions`

Represents one registered supervised model version produced by the ML pipeline.

Required fields:

| Field | Purpose |
| --- | --- |
| `model_name` | Stable logical model name |
| `model_version` | Version derived from MLflow run id |
| `target_name` | Official prediction target |
| `training_dataset_version_id` | Exact dataset used to train |
| `scoring_dataset_version_id` | Exact dataset used to score |
| `training_window_start` / `training_window_end` | Temporal scope of the model |
| `metrics_json` | Holdout metrics exposed to the application |
| `artifact_uri` | MLflow artifact location |
| `status` | Lifecycle state |

Optional fields:
- none for the MVP

Consumer-facing fields:
- `model_name`
- `model_version`
- `target_name`
- `training_window_start`
- `training_window_end`
- `metrics_json`
- `status`

## Consumer Exposure Policy

The following rules MUST be followed by API and chat implementations:

- Consumer-facing dataset metadata MAY be returned directly in evidence payloads.
- Pipeline-run internals SHALL NOT be returned to end users by default.
- Lineage edges SHALL remain internal unless a governance or admin endpoint explicitly exposes them.
- Audit events SHALL remain internal unless an audit-specific endpoint exposes them.
- Model metrics MAY be returned in predictive answers because they are part of prediction disclosure.

## Chat and API Contracts

### Factual response payload

Every factual response must expose:
- `answer`
- `sources[]`
- `dataset_versions[]`
- `time_window`
- `geographic_scope`
- `gold_product`
- `evidence_summary`

Recommended payload shape:

```json
{
  "answer": "Burglary was the most frequent crime type in Westminster 001A in 2024-01.",
  "sources": [
    {
      "source_name": "data.police.uk",
      "logical_name": "crime_metrics_area_month_category",
      "dataset_version_id": "9a7b2d88-38f1-4cad-8f02-3c422f0fa8a1"
    }
  ],
  "dataset_versions": [
    {
      "id": "9a7b2d88-38f1-4cad-8f02-3c422f0fa8a1",
      "layer": "gold",
      "logical_name": "crime_metrics_area_month_category",
      "version": "2024-01",
      "valid_from": "2024-01",
      "status": "available"
    }
  ],
  "time_window": "2024-01",
  "geographic_scope": "E01004736",
  "gold_product": "gold/analytics/crime_metrics_area_month_category",
  "evidence_summary": "2 burglary incidents were registered in the selected period and area."
}
```

### Predictive response payload

Every predictive response must expose:
- `answer`
- `historical_context`
- `prediction`
- `prediction_horizon`
- `model_name`
- `model_version`
- `quality_metrics`
- `dataset_versions[]`
- `gold_product`
- `warning`

Prediction outputs must never be presented as observed facts.
Prediction outputs MUST include model disclosure fields even when the answer is rendered in natural language.

Recommended payload shape:

```json
{
  "answer": "The estimated burglary volume for next month is 11 incidents.",
  "historical_context": "The area recorded 10, 12, and 9 incidents in the previous observed months.",
  "prediction": {
    "value": 11.0,
    "target_name": "incident_count_next_period",
    "prediction_horizon": "2024-04"
  },
  "prediction_horizon": "2024-04",
  "model_name": "crime_count_forecaster",
  "model_version": "mlflow-run-id",
  "quality_metrics": {
    "mae": 1.8,
    "rmse": 2.4,
    "mape": 0.17
  },
  "dataset_versions": [
    {
      "id": "9a7b2d88-38f1-4cad-8f02-3c422f0fa8a1",
      "layer": "gold",
      "logical_name": "forecast_scoring_set",
      "version": "2024-03",
      "valid_from": "2024-03",
      "status": "available"
    }
  ],
  "gold_product": "gold/ml/forecast_predictions",
  "warning": "Prediction generated from a supervised model and subject to forecast uncertainty."
}
```

## Prediction Disclosure Rules

- Predictive answers MUST include a human-readable uncertainty warning.
- Predictive answers MUST include the model name and model version.
- Predictive answers MUST include holdout quality metrics.
- Predictive answers MUST separate historical observations from future estimates.
- Predictive answers SHALL NOT imply that a forecasted incident count is already observed in the source dataset.

## Access Rules

- `admin` can read and publish all layers and governance metadata.
- `analyst` can read Gold datasets and inspect dataset and model version metadata.
- `manager` can read executive Gold analytics but not operational pipeline metadata.
- `operator` can read the Gold product needed for operational context, without model internals.

## Ownership Boundary Between Gold Products

- `Gold Analytics` SHALL be the source of truth for factual structured answers and rankings.
- `Gold RAG` SHALL be the source of truth for evidence-oriented text chunks and retrieval context.
- `Gold ML` SHALL be the source of truth for supervised model training, scoring, and prediction outputs.
- Downstream teams MUST NOT collapse these three product families into one shared dataset contract.

## Default Modeling Contract

- Primary supervised target: `incident_count_next_period`
- Canonical feature grain: `lsoa_code + reference_month + crime_type`
- Temporal split is mandatory for training and evaluation
- Gold ML is prepared for regression first, with later extension for classification
