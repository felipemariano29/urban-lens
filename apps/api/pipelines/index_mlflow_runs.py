"""Index MLflow run summaries into the knowledge corpus for RAG retrieval."""

from __future__ import annotations

import argparse
import logging
from typing import Any

from mlflow.client import MlflowClient

from urban_lens.core.settings import AppConfig
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.vector_store import MilvusVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_SENSITIVE_PARAM_MARKERS = {
    "prompt",
    "system_prompt",
    "template",
    "artifact_uri",
    "secret",
    "token",
    "password",
    "key",
}


def _fetch_mlflow_experiments(client: MlflowClient) -> list[Any]:
    """Fetch all experiments from MLflow using the official client."""
    try:
        return list(client.search_experiments())
    except Exception as exc:
        logger.error("Failed to fetch experiments: %s", exc)
        return []


def _fetch_mlflow_runs(client: MlflowClient, experiment_id: str, max_results: int = 100) -> list[Any]:
    """Fetch runs for an experiment from MLflow using the official client."""
    try:
        return list(client.search_runs(experiment_ids=[experiment_id], max_results=max_results))
    except Exception as exc:
        logger.error("Failed to fetch runs for experiment %s: %s", experiment_id, exc)
        return []


def _run_info(run: Any) -> Any:
    return run.info if hasattr(run, "info") else run.get("info", {})


def _run_data(run: Any) -> Any:
    return run.data if hasattr(run, "data") else run.get("data", {})


def _format_run_content(run: Any, experiment_name: str) -> str:
    """Format MLflow run data into readable content for RAG."""
    info = _run_info(run)
    data = _run_data(run)

    run_id = getattr(info, "run_id", None) or info.get("run_id", "unknown")
    run_name = getattr(info, "run_name", None) or info.get("run_name", run_id[:8])
    status = getattr(info, "status", None) or info.get("status", "unknown")
    start_time = getattr(info, "start_time", None) or info.get("start_time", "")
    end_time = getattr(info, "end_time", None) or info.get("end_time", "")

    raw_metrics = getattr(data, "metrics", None) or data.get("metrics", {})
    if isinstance(raw_metrics, dict):
        metrics = [{"key": key, "value": value} for key, value in raw_metrics.items()]
    else:
        metrics = list(raw_metrics)
    params = [
        p for p in _params_as_rows(data)
        if not _is_sensitive_param_key(str(p.get("key", "")))
    ]

    # Format metrics
    metrics_text = "\n".join([
        f"  - {m.get('key')}: {m.get('value')}"
        for m in metrics
    ]) or "  No metrics recorded"

    # Format params
    params_text = "\n".join([
        f"  - {p.get('key')}: {p.get('value')}"
        for p in params
    ]) or "  No parameters recorded"

    content = f"""MLflow Run: {run_name}
Experiment: {experiment_name}
Run ID: {run_id}
Status: {status}
Start Time: {start_time}
End Time: {end_time}

Metrics:
{metrics_text}

Parameters:
{params_text}

This run is part of the Urban Lens forecasting pipeline which predicts crime trends."""

    return content


def _format_run_title(run: Any, experiment_name: str) -> str:
    """Generate a title for the run chunk."""
    info = _run_info(run)
    run_id = getattr(info, "run_id", None) or info.get("run_id", "unknown")
    run_name = getattr(info, "run_name", None) or info.get("run_name", run_id[:8])
    return f"MLflow Run: {run_name} ({experiment_name})"


def _is_sensitive_param_key(key: str) -> bool:
    normalized = key.strip().lower()
    return any(marker in normalized for marker in _SENSITIVE_PARAM_MARKERS)


def _params_as_rows(data: Any) -> list[dict[str, Any]]:
    raw_params = getattr(data, "params", None) or data.get("params", {})
    if isinstance(raw_params, dict):
        return [{"key": key, "value": value} for key, value in raw_params.items()]
    return list(raw_params)


def index_mlflow_runs(config: AppConfig, max_runs_per_experiment: int = 50) -> int:
    """Index all MLflow runs into the knowledge corpus.

    Returns the number of chunks indexed.
    """
    embedder = OllamaEmbedder(config.ollama_base_url, config.embedding_model)
    vector_store = MilvusVectorStore(config.milvus_uri)

    # Ensure knowledge collection exists
    vector_store.ensure_knowledge_collection()

    client = MlflowClient(tracking_uri=config.mlflow_tracking_uri)
    experiments = _fetch_mlflow_experiments(client)
    logger.info("Found %d experiments in MLflow", len(experiments))

    records: list[dict[str, object]] = []

    for exp in experiments:
        exp_id = getattr(exp, "experiment_id", None) or exp.get("experiment_id", "")
        exp_name = getattr(exp, "name", None) or exp.get("name", "unknown")

        if exp_name.startswith("_"):  # Skip internal experiments
            continue

        runs = _fetch_mlflow_runs(client, exp_id, max_runs_per_experiment)
        logger.info("Found %d runs in experiment %s", len(runs), exp_name)

        for run in runs:
            info = _run_info(run)
            run_id = getattr(info, "run_id", None) or info.get("run_id", "")
            if not run_id:
                continue

            content = _format_run_content(run, exp_name)
            title = _format_run_title(run, exp_name)

            # Generate embedding
            embeddings = embedder.embed([content])
            if not embeddings:
                logger.warning("Failed to generate embedding for run %s", run_id)
                continue

            records.append({
                "chunk_id": f"mlflow_run_{run_id}",
                "chunk_type": "mlflow_run",
                "source_type": "mlflow",
                "title": title,
                "content": content,
                "run_id": run_id,
                "experiment_id": exp_id,
                "reference": f"mlflow:{exp_name}:{run_id}",
                "embedding": embeddings[0],
            })

    if not records:
        logger.info("No MLflow runs to index")
        return 0

    # Upsert all records
    count = vector_store.upsert_knowledge_chunks(records)
    logger.info("Indexed %d MLflow run chunks into knowledge corpus", count)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Index MLflow runs into knowledge corpus")
    parser.add_argument("--max-runs", type=int, default=50, help="Max runs per experiment")
    args = parser.parse_args()

    config = AppConfig.from_env()
    indexed = index_mlflow_runs(config, args.max_runs)
    print(f"Indexed {indexed} MLflow run chunks")


if __name__ == "__main__":
    main()
