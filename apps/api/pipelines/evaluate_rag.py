"""RAG evaluation framework with MLflow tracking."""

from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from urban_lens.core.settings import AppConfig
from urban_lens.rag.contracts import AccessProfile, RagFilters, RagQuery
from urban_lens.rag.pipeline import RagPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class EvalQuestion:
    """A question with expected properties for evaluation."""

    question: str
    expected_intent: str = ""
    expected_corpus: str = ""  # "crime", "knowledge", or "hybrid"
    expected_keywords: list[str] = field(default_factory=list)
    min_context_score: float = 0.3
    max_latency_ms: float = 5000.0
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """Result of evaluating a single question."""

    question: str
    status: str  # "pass", "fail", "error"
    answer: str
    intent_detected: str
    corpus_used: str
    context_count: int
    max_context_score: float
    latency_ms: float
    keywords_found: list[str]
    keywords_missing: list[str]
    errors: list[str] = field(default_factory=list)


@dataclass
class EvalSummary:
    """Summary of evaluation run."""

    total: int
    passed: int
    failed: int
    errors: int
    avg_latency_ms: float
    avg_context_score: float
    pass_rate: float


# Default evaluation dataset
DEFAULT_EVAL_QUESTIONS = [
    # Crime-related questions
    EvalQuestion(
        question="What crimes were most common in January 2024?",
        expected_intent="crime_type_listing",
        expected_corpus="crime",
        expected_keywords=["crime", "january", "2024"],
        tags=["crime", "temporal"],
    ),
    EvalQuestion(
        question="What is the dominant crime type in London?",
        expected_intent="dominant_crime",
        expected_corpus="crime",
        expected_keywords=["crime"],
        tags=["crime", "dominant"],
    ),
    EvalQuestion(
        question="Compare burglary rates in 2023 vs 2024",
        expected_intent="comparison",
        expected_corpus="crime",
        expected_keywords=["burglary", "2023", "2024"],
        tags=["crime", "comparison"],
    ),
    # Platform knowledge questions
    EvalQuestion(
        question="How does Urban Lens work?",
        expected_intent="platform_knowledge",
        expected_corpus="knowledge",
        expected_keywords=["urban", "lens"],
        tags=["platform"],
    ),
    EvalQuestion(
        question="What MLflow experiments are available?",
        expected_intent="platform_knowledge",
        expected_corpus="knowledge",
        expected_keywords=["mlflow", "experiment"],
        tags=["platform", "mlflow"],
    ),
    EvalQuestion(
        question="Show me the forecast model metrics",
        expected_intent="platform_knowledge",
        expected_corpus="knowledge",
        expected_keywords=["forecast", "model", "metrics"],
        tags=["platform", "mlflow"],
    ),
    EvalQuestion(
        question="Quem e voce?",
        expected_intent="platform_knowledge",
        expected_corpus="knowledge",
        expected_keywords=["urban", "lens"],
        tags=["platform", "pt"],
    ),
    EvalQuestion(
        question="Quais modelos foram treinados e quais metricas foram utilizadas?",
        expected_intent="platform_knowledge",
        expected_corpus="knowledge",
        expected_keywords=["ridge", "randomforest", "mae"],
        tags=["platform", "pt", "mlflow"],
    ),
    EvalQuestion(
        question="Qual foi o pre-processamento realizado nos dados?",
        expected_intent="platform_knowledge",
        expected_corpus="knowledge",
        expected_keywords=["snake_case", "lag", "onehotencoder"],
        tags=["platform", "pt"],
    ),
    # Generic questions
    EvalQuestion(
        question="Tell me about crime trends",
        expected_intent="generic",
        expected_corpus="hybrid",
        expected_keywords=["crime"],
        tags=["generic"],
    ),
]


def load_eval_dataset(path: Path | None) -> list[EvalQuestion]:
    """Load evaluation dataset from JSON file or use defaults."""
    if path is None or not path.exists():
        logger.info("Using default evaluation dataset (%d questions)", len(DEFAULT_EVAL_QUESTIONS))
        return DEFAULT_EVAL_QUESTIONS

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = [
        EvalQuestion(
            question=q["question"],
            expected_intent=q.get("expected_intent", ""),
            expected_corpus=q.get("expected_corpus", ""),
            expected_keywords=q.get("expected_keywords", []),
            min_context_score=q.get("min_context_score", 0.3),
            max_latency_ms=q.get("max_latency_ms", 5000.0),
            tags=q.get("tags", []),
        )
        for q in data.get("questions", [])
    ]
    logger.info("Loaded %d questions from %s", len(questions), path)
    return questions


def evaluate_question(pipeline: RagPipeline, question: EvalQuestion) -> EvalResult:
    """Evaluate a single question against the RAG pipeline."""
    from urban_lens.rag.query_understanding import detect_query_intent, intent_to_corpus

    errors: list[str] = []
    intent_detected = detect_query_intent(question.question)
    corpus_used = intent_to_corpus(intent_detected)

    start = time.perf_counter()
    try:
        response = pipeline.run(
            RagQuery(
                query=question.question,
                filters=RagFilters(),
                profile=AccessProfile.admin,
                top_k=5,
                min_score=0.2,
                model=pipeline.config.chat_model,
            )
        )
        latency_ms = (time.perf_counter() - start) * 1000
    except Exception as e:
        return EvalResult(
            question=question.question,
            status="error",
            answer="",
            intent_detected=intent_detected,
            corpus_used=corpus_used,
            context_count=0,
            max_context_score=0.0,
            latency_ms=0.0,
            keywords_found=[],
            keywords_missing=question.expected_keywords,
            errors=[str(e)],
        )

    answer = response.answer.text
    context_count = len(response.context)
    max_context_score = max((c.score for c in response.context), default=0.0)

    # Check keywords in answer
    answer_lower = answer.lower()
    keywords_found = [kw for kw in question.expected_keywords if kw.lower() in answer_lower]
    keywords_missing = [kw for kw in question.expected_keywords if kw.lower() not in answer_lower]

    # Determine pass/fail
    status = "pass"

    if question.expected_intent and intent_detected != question.expected_intent:
        errors.append(f"Intent mismatch: expected {question.expected_intent}, got {intent_detected}")
        status = "fail"

    if question.expected_corpus and corpus_used != question.expected_corpus:
        errors.append(f"Corpus mismatch: expected {question.expected_corpus}, got {corpus_used}")
        status = "fail"

    if max_context_score < question.min_context_score:
        errors.append(f"Low context score: {max_context_score:.2f} < {question.min_context_score}")
        status = "fail"

    if latency_ms > question.max_latency_ms:
        errors.append(f"High latency: {latency_ms:.0f}ms > {question.max_latency_ms}ms")
        status = "fail"

    if keywords_missing:
        errors.append(f"Missing keywords in answer: {keywords_missing}")
        # Don't fail on missing keywords, just warn

    return EvalResult(
        question=question.question,
        status=status,
        answer=answer,
        intent_detected=intent_detected,
        corpus_used=corpus_used,
        context_count=context_count,
        max_context_score=max_context_score,
        latency_ms=latency_ms,
        keywords_found=keywords_found,
        keywords_missing=keywords_missing,
        errors=errors,
    )


def run_evaluation(
    config: AppConfig,
    dataset_path: Path | None = None,
    tags_filter: list[str] | None = None,
) -> tuple[list[EvalResult], EvalSummary]:
    """Run evaluation on all questions and return results."""
    pipeline = RagPipeline(config)
    questions = load_eval_dataset(dataset_path)

    # Filter by tags if specified
    if tags_filter:
        questions = [q for q in questions if any(t in q.tags for t in tags_filter)]
        logger.info("Filtered to %d questions with tags %s", len(questions), tags_filter)

    results: list[EvalResult] = []
    for i, question in enumerate(questions, 1):
        logger.info("[%d/%d] Evaluating: %s", i, len(questions), question.question[:50])
        result = evaluate_question(pipeline, question)
        results.append(result)
        logger.info("  -> %s (latency: %.0fms, score: %.2f)", result.status, result.latency_ms, result.max_context_score)

    # Calculate summary
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    errors = sum(1 for r in results if r.status == "error")
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0.0
    avg_score = sum(r.max_context_score for r in results) / len(results) if results else 0.0

    summary = EvalSummary(
        total=len(results),
        passed=passed,
        failed=failed,
        errors=errors,
        avg_latency_ms=avg_latency,
        avg_context_score=avg_score,
        pass_rate=passed / len(results) if results else 0.0,
    )

    return results, summary


def log_to_mlflow(results: list[EvalResult], summary: EvalSummary, config: AppConfig) -> str | None:
    """Log evaluation results to MLflow."""
    try:
        import mlflow
    except ImportError:
        logger.warning("MLflow not installed, skipping MLflow logging")
        return None

    mlflow.set_tracking_uri(config.mlflow_tracking_uri)
    mlflow.set_experiment("rag_evaluation")

    with mlflow.start_run() as run:
        # Log summary metrics
        mlflow.log_metric("total_questions", summary.total)
        mlflow.log_metric("passed", summary.passed)
        mlflow.log_metric("failed", summary.failed)
        mlflow.log_metric("errors", summary.errors)
        mlflow.log_metric("pass_rate", summary.pass_rate)
        mlflow.log_metric("avg_latency_ms", summary.avg_latency_ms)
        mlflow.log_metric("avg_context_score", summary.avg_context_score)

        # Log params
        mlflow.log_param("embedding_model", config.embedding_model)
        mlflow.log_param("chat_model", config.chat_model)

        # Log results as artifact
        results_data = [
            {
                "question": r.question,
                "status": r.status,
                "intent": r.intent_detected,
                "corpus": r.corpus_used,
                "latency_ms": r.latency_ms,
                "context_score": r.max_context_score,
                "errors": r.errors,
            }
            for r in results
        ]
        mlflow.log_dict({"results": results_data}, "eval_results.json")

        logger.info("Logged evaluation to MLflow run: %s", run.info.run_id)
        return run.info.run_id

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline")
    parser.add_argument("--dataset", type=Path, help="Path to evaluation dataset JSON")
    parser.add_argument("--tags", nargs="+", help="Filter questions by tags")
    parser.add_argument("--mlflow", action="store_true", help="Log results to MLflow")
    args = parser.parse_args()

    config = AppConfig.from_env()
    results, summary = run_evaluation(config, args.dataset, args.tags)

    print("\n=== RAG Evaluation Summary ===")
    print(f"Total: {summary.total}")
    print(f"Passed: {summary.passed} ({summary.pass_rate:.1%})")
    print(f"Failed: {summary.failed}")
    print(f"Errors: {summary.errors}")
    print(f"Avg Latency: {summary.avg_latency_ms:.0f}ms")
    print(f"Avg Context Score: {summary.avg_context_score:.2f}")

    if args.mlflow:
        run_id = log_to_mlflow(results, summary, config)
        if run_id:
            print(f"MLflow Run ID: {run_id}")


if __name__ == "__main__":
    main()
