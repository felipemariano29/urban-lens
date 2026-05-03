from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from mlflow.client import MlflowClient
from mlflow.entities import Run, ViewType

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import get_mlflow_client, require_roles
from urban_lens.api.schemas import RunMetadataResponse, RunMetricsSchema

require_admin = require_roles("admin", "internal_service")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metadata", tags=["MLflow Metadata"])

_DEFAULT_EXPERIMENT_NAME = "urban-lens-medallion"
_DATASET_VERSION_PARAM = "training_dataset_version_id"


def _ms_to_utc(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def _build_filter_string(
    dataset_version: str | None,
    start_date: date | None,
    end_date: date | None,
) -> str:
    clauses: list[str] = []

    if dataset_version is not None:
        clauses.append(f"params.{_DATASET_VERSION_PARAM} = '{dataset_version}'")

    return " AND ".join(clauses) if clauses else ""


def _resolve_experiment_ids(
    client: MlflowClient,
    experiment_name: str | None,
) -> list[str]:
    name = experiment_name or _DEFAULT_EXPERIMENT_NAME
    experiment = client.get_experiment_by_name(name)

    if experiment_name is not None and experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MLflow experiment '{experiment_name}' not found.",
        )

    if experiment is not None:
        return [experiment.experiment_id]

    all_experiments = client.search_experiments(view_type=ViewType.ACTIVE_ONLY)
    return [exp.experiment_id for exp in all_experiments]


def _build_run_response(run: Run, experiment_name: str) -> RunMetadataResponse:
    raw_metrics = run.data.metrics
    raw_params = {k: str(v) for k, v in run.data.params.items()}

    return RunMetadataResponse(
        run_id=run.info.run_id,
        experiment_id=run.info.experiment_id,
        experiment_name=experiment_name,
        run_name=run.info.run_name or None,
        status=run.info.status,
        start_time=_ms_to_utc(run.info.start_time),
        end_time=_ms_to_utc(run.info.end_time),
        artifact_uri=run.info.artifact_uri or None,
        metrics=RunMetricsSchema(
            mae=raw_metrics.get("mae"),
            rmse=raw_metrics.get("rmse"),
            mape=raw_metrics.get("mape"),
        ),
        params=raw_params,
        dataset_version=raw_params.get(_DATASET_VERSION_PARAM),
    )


@router.get(
    "/runs",
    response_model=List[RunMetadataResponse],
    summary="List MLflow experiment runs with metadata",
    description=(
        "Returns a structured list of MLflow training runs for the Urban Lens "
        "forecast pipeline. Results can be narrowed by experiment name, "
        "training dataset version, and a creation-time window. "
        "**Requires the `x-profile-name: admin` header.**"
    ),
    responses={
        200: {"description": "Filtered list of run metadata records."},
        403: {"description": "Forbidden — caller does not hold the 'admin' profile."},
        404: {"description": "The requested experiment name was not found in MLflow."},
    },
)
def list_runs(
    experiment_name: Optional[str] = Query(
        None,
        description=(
            "Filter by MLflow experiment name. "
            f"Defaults to '{_DEFAULT_EXPERIMENT_NAME}' when omitted."
        ),
    ),
    dataset_version: Optional[str] = Query(
        None,
        description=(
            "Filter runs by the training dataset version identifier stored in "
            f"the '{_DATASET_VERSION_PARAM}' MLflow parameter (e.g. '2024-01')."
        ),
    ),
    start_date: Optional[date] = Query(
        None,
        description="Include only runs that started on or after this date (ISO 8601, e.g. '2024-01-01').",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Include only runs that started on or before this date (ISO 8601, e.g. '2024-12-31').",
    ),
    _profile: UserProfile = Depends(require_admin),
    mlflow_client: MlflowClient = Depends(get_mlflow_client),
) -> List[RunMetadataResponse]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'start_date' must not be later than 'end_date'.",
        )

    experiment_ids = _resolve_experiment_ids(mlflow_client, experiment_name)

    if not experiment_ids:
        logger.info("No active experiments found in MLflow — returning empty result set.")
        return []

    resolved_name = experiment_name or _DEFAULT_EXPERIMENT_NAME
    experiment_obj = mlflow_client.get_experiment_by_name(resolved_name)
    display_name = experiment_obj.name if experiment_obj else resolved_name

    filter_string = _build_filter_string(dataset_version, start_date, end_date)

    logger.debug(
        "Searching MLflow runs — experiment_ids=%s filter='%s'",
        experiment_ids,
        filter_string,
    )

    runs = mlflow_client.search_runs(
        experiment_ids=experiment_ids,
        filter_string=filter_string,
        run_view_type=ViewType.ACTIVE_ONLY,
        order_by=["attributes.start_time DESC"],
    )

    result = []
    for run in runs:
        run_dt = _ms_to_utc(run.info.start_time)
        if run_dt:
            run_date = run_dt.date()
            if start_date and run_date < start_date:
                continue
            if end_date and run_date > end_date:
                continue
        result.append(_build_run_response(run, display_name))

    return result