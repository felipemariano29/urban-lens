"""Index MLflow run summaries into the knowledge corpus for RAG retrieval."""

from __future__ import annotations

import argparse
import json
import logging
import urllib.request
from typing import Any

from urban_lens.core.settings import AppConfig
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.vector_store import MilvusVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _fetch_mlflow_experiments(mlflow_uri: str) -> list[dict[str, Any]]:
    """Fetch all experiments from MLflow."""
    url = f"{mlflow_uri.rstrip('/')}/api/2.0/mlflow/experiments/search"
    request = urllib.request.Request(
        url,
        data=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("experiments", [])
    except Exception as e:
        logger.error("Failed to fetch experiments: %s", e)
        return []


def _fetch_mlflow_runs(mlflow_uri: str, experiment_id: str, max_results: int = 100) -> list[dict[str, Any]]:
    """Fetch runs for an experiment from MLflow."""
    url = f"{mlflow_uri.rstrip('/')}/api/2.0/mlflow/runs/search"
    request = urllib.request.Request(
        url,
        data=json.dumps({
            "experiment_ids": [experiment_id],
            "max_results": max_results,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("runs", [])
    except Exception as e:
        logger.error("Failed to fetch runs for experiment %s: %s", experiment_id, e)
        return []


def _format_run_content(run: dict[str, Any], experiment_name: str) -> str:
    """Format MLflow run data into readable content for RAG."""
    info = run.get("info", {})
    data = run.get("data", {})

    run_id = info.get("run_id", "unknown")
    run_name = info.get("run_name", run_id[:8])
    status = info.get("status", "unknown")
    start_time = info.get("start_time", "")
    end_time = info.get("end_time", "")

    metrics = data.get("metrics", [])
    params = data.get("params", [])

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


def _format_run_title(run: dict[str, Any], experiment_name: str) -> str:
    """Generate a title for the run chunk."""
    info = run.get("info", {})
    run_name = info.get("run_name", info.get("run_id", "unknown")[:8])
    return f"MLflow Run: {run_name} ({experiment_name})"


def index_mlflow_runs(config: AppConfig, max_runs_per_experiment: int = 50) -> int:
    """Index all MLflow runs into the knowledge corpus.

    Returns the number of chunks indexed.
    """
    embedder = OllamaEmbedder(config.ollama_base_url, config.embedding_model)
    vector_store = MilvusVectorStore(config.milvus_uri)

    # Ensure knowledge collection exists
    vector_store.ensure_knowledge_collection()

    mlflow_uri = config.mlflow_tracking_uri
    experiments = _fetch_mlflow_experiments(mlflow_uri)
    logger.info("Found %d experiments in MLflow", len(experiments))

    records: list[dict[str, object]] = []

    for exp in experiments:
        exp_id = exp.get("experiment_id", "")
        exp_name = exp.get("name", "unknown")

        if exp_name.startswith("_"):  # Skip internal experiments
            continue

        runs = _fetch_mlflow_runs(mlflow_uri, exp_id, max_runs_per_experiment)
        logger.info("Found %d runs in experiment %s", len(runs), exp_name)

        for run in runs:
            info = run.get("info", {})
            run_id = info.get("run_id", "")
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
