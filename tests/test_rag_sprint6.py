from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import jwt as pyjwt
from fastapi.testclient import TestClient

from urban_lens.core.settings import AppConfig
from urban_lens.rag.contracts import AccessProfile, RagQuery
from urban_lens.rag.generation import build_prompt, detect_question_language, remove_repeated_question_prefix
from urban_lens.rag.pipeline import RagPipeline

_JWT_SECRET = "test-secret-32-bytes-long-padded!"
_JWT_ALGO = "HS256"


def _token(role: str) -> str:
    return pyjwt.encode({"role": role, "sub": "tester"}, _JWT_SECRET, algorithm=_JWT_ALGO)


def _auth(role: str) -> dict:
    return {"Authorization": f"Bearer {_token(role)}"}


FAKE_CONFIG = AppConfig(
    s3_endpoint_url="http://localhost:9000",
    s3_access_key="test",
    s3_secret_key="test",
    s3_bucket="test",
    s3_region="us-east-1",
    s3_secure=False,
    postgres_dsn="postgresql://test:test@localhost:5432/test",
    mlflow_tracking_uri="http://localhost:5005",
    artifact_dir=Path(".artifacts"),
    milvus_uri="http://localhost:19530",
    ollama_base_url="http://localhost:11434",
    embedding_model="nomic-embed-text",
    cors_origins=["*"],
)


class FakeEmbedder:
    def embed(self, texts):
        return [[0.1] * 768 for _ in texts]


class FakeVectorStore:
    def __init__(self, hits):
        self.hits = hits
        self.captured_filters = None

    def search(self, query_embedding, top_k=5, filters=None):
        self.captured_filters = filters
        return self.hits[:top_k]


class FakeGenerator:
    def __init__(self):
        self.prompt = ""

    def generate(self, prompt, model):
        self.prompt = prompt
        return "A resposta esta sustentada pelas evidencias [E1]."


def _crime_hit(score=0.88):
    return {
        "distance": score,
        "entity": {
            "chunk_id": "crime-1",
            "chunk_type": "area_month_category",
            "reference_month": "2024-01",
            "lsoa_code": "E01001234",
            "crime_type": "burglary",
            "title": "Westminster 2024-01 burglary",
            "content": "In 2024-01, Westminster recorded 12 burglary incidents.",
            "dataset_version_id": "dataset-v1",
        },
    }


def _technical_hit():
    return {
        "distance": 0.91,
        "entity": {
            "chunk_id": "run-1",
            "chunk_type": "experiment_metadata",
            "title": "Forecast experiment",
            "content": "Forecast model run finished with quality metrics.",
            "dataset_version_id": "run-ref",
            "run_id": "secret-run",
            "artifact_uri": "s3://private-artifacts/run",
        },
    }


def test_pipeline_returns_answer_with_evidence_citations():
    generator = FakeGenerator()
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_crime_hit()]),
        generator=generator,
    )

    response = pipeline.run(RagQuery(query="burglary?", profile=AccessProfile.intel_user))

    assert response.answer.status == "answered"
    assert response.evidences[0].id == "E1"
    assert response.evidences[0].reference == "dataset-v1:2024-01"
    assert "[E1]" in generator.prompt


def test_pipeline_falls_back_when_evidence_score_is_too_low():
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_crime_hit(score=0.01)]),
        generator=FakeGenerator(),
    )

    response = pipeline.run(RagQuery(query="burglary?", profile=AccessProfile.intel_user, min_score=0.15))

    assert response.answer.status == "insufficient_evidence"
    assert response.fallback_reason == "insufficient_retrieved_evidence"


def test_intel_user_cannot_receive_technical_experiment_metadata():
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_technical_hit(), _crime_hit()]),
        generator=FakeGenerator(),
    )

    response = pipeline.run(RagQuery(query="experimento?", profile=AccessProfile.intel_user))

    assert [chunk.id for chunk in response.context] == ["crime-1"]
    assert all("run_id" not in evidence.metadata for evidence in response.evidences)


def test_developer_receives_authorized_technical_metadata_without_private_fields():
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_technical_hit()]),
        generator=FakeGenerator(),
    )

    response = pipeline.run(RagQuery(query="experimento?", profile=AccessProfile.developer))

    assert response.context[0].metadata["run_id"] == "secret-run"
    assert "artifact_uri" not in response.context[0].metadata


def test_chat_endpoint_accepts_sprint6_profiles(monkeypatch):
    monkeypatch.setenv("URBAN_LENS_JWT_SECRET", _JWT_SECRET)
    from urban_lens.api.main import app

    mock_response = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_crime_hit()]),
        generator=FakeGenerator(),
    ).run(RagQuery(query="burglary?", profile=AccessProfile.developer))

    with TestClient(app, raise_server_exceptions=False) as client:
        with patch("urban_lens.api.services.rag_service.run_chat_query", return_value=mock_response):
            response = client.post("/api/v1/chat/query", json={"query": "burglary?"}, headers=_auth("developer"))

    assert response.status_code == 200
    assert response.json()["profile"] == "developer"


def test_generation_cleanup_removes_repeated_question_prefix():
    answer = "Quais evidências sustentam burglary?\n\nApenas [E1] sustenta a resposta."

    cleaned = remove_repeated_question_prefix(answer, "Quais evidencias sustentam burglary?")

    assert cleaned == "Apenas [E1] sustenta a resposta."


def test_prompt_uses_portuguese_instructions_for_portuguese_question():
    prompt = build_prompt(
        "Quais evidencias sustentam burglary?",
        "[E1] evidence",
        AccessProfile.developer,
    )

    assert detect_question_language("Quais evidencias sustentam burglary?") == "pt"
    assert "Responda somente em portugues" in prompt
