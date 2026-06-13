from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import jwt as pyjwt
from fastapi.testclient import TestClient

from urban_lens.core.settings import AppConfig
from urban_lens.rag.contracts import AccessProfile, RagQuery
from urban_lens.rag.generation import (
    OllamaGenerator,
    build_prompt,
    detect_question_language,
    infer_answer_shape,
    remove_repeated_question_prefix,
)
from urban_lens.rag.pipeline import RagPipeline
from urban_lens.rag.retrieval import milvus_hits_to_context

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
        self.search_calls = []

    def search(self, query_embedding, top_k=5, filters=None):
        self.captured_filters = filters
        self.search_calls.append({"top_k": top_k, "filters": filters})
        return self.hits[:top_k]

    def search_knowledge(self, query_embedding, top_k=5, filters=None):
        self.search_calls.append({"top_k": top_k, "filters": filters, "corpus": "knowledge"})
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
            "chunk_type": "mlflow_run",
            "title": "Forecast experiment",
            "content": "Forecast model run finished with quality metrics.",
            "dataset_version_id": "run-ref",
            "run_id": "secret-run",
            "artifact_uri": "s3://private-artifacts/run",
        },
    }


def _platform_doc_hit():
    return {
        "distance": 0.93,
        "entity": {
            "chunk_id": "doc-1",
            "chunk_type": "documentation",
            "source_type": "docs",
            "title": "assistant-knowledge > Quais modelos foram treinados e quais metricas foram utilizadas",
            "content": "O pipeline baseline avalia Ridge, RandomForestRegressor e ExtraTreesRegressor com MAE, RMSE e MAPE.",
            "dataset_version_id": "docs-run",
            "document_category": "platform",
            "reference": "docs:assistant-knowledge > Quais modelos foram treinados e quais metricas foram utilizadas",
        },
    }


def _duplicate_crime_hit(chunk_id: str, title: str, score: float = 0.88):
    hit = _crime_hit(score=score)
    hit["entity"] = {**hit["entity"], "chunk_id": chunk_id, "title": title}
    return hit


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


def test_pipeline_infers_lsoa_filter_from_question():
    vector_store = FakeVectorStore([_crime_hit()])
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        generator=FakeGenerator(),
    )

    pipeline.run(RagQuery(query="Quais crimes ocorreram na area E01001234?", profile=AccessProfile.intel_user))

    assert vector_store.search_calls[0]["filters"] == {"lsoa_code": "E01001234"}
    assert vector_store.search_calls[1]["filters"] == {
        "lsoa_code": "E01001234",
        "chunk_type": "area_month_category",
    }


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


def test_pipeline_uses_portuguese_fallback_for_portuguese_question():
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_crime_hit(score=0.01)]),
        generator=FakeGenerator(),
    )

    response = pipeline.run(
        RagQuery(query="Qual foi o tipo de crime dominante em Westminster?", profile=AccessProfile.intel_user)
    )

    assert response.answer.status == "insufficient_evidence"
    assert response.answer.text.startswith("Nao ha evidencia suficiente")


def test_intel_user_receives_authorized_platform_knowledge_without_sensitive_metadata():
    vector_store = FakeVectorStore([_platform_doc_hit()])
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        generator=FakeGenerator(),
    )

    response = pipeline.run(
        RagQuery(query="Quais modelos foram treinados e quais metricas foram utilizadas?", profile=AccessProfile.intel_user)
    )

    assert [chunk.id for chunk in response.context] == ["doc-1"]
    assert all("run_id" not in evidence.metadata for evidence in response.evidences)
    assert response.context[0].metadata["source_type"] == "docs"
    assert vector_store.search_calls[0]["filters"] == {"source_type": "docs", "document_category": "platform"}


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


def test_pipeline_composes_structured_crime_type_listing_for_area_query():
    area_hits = [
        {
            "distance": 0.96,
            "entity": {
                "chunk_id": "area-cat-1",
                "chunk_type": "area_month_category",
                "reference_month": "2026-01",
                "lsoa_code": "E01000001",
                "crime_type": "vehicle_crime",
                "title": "2026-01 City of London 001A vehicle_crime",
                "content": (
                    "In 2026-01, area City of London 001A (E01000001) recorded 3 incidents for crime type "
                    "vehicle_crime. This represented 25.0% of all incidents in the area and ranked #1 among crime "
                    "types for that area-month."
                ),
                "dataset_version_id": "dataset-v1",
            },
        },
        {
            "distance": 0.93,
            "entity": {
                "chunk_id": "area-cat-2",
                "chunk_type": "area_month_category",
                "reference_month": "2026-01",
                "lsoa_code": "E01000001",
                "crime_type": "drugs",
                "title": "2026-01 City of London 001A drugs",
                "content": (
                    "In 2026-01, area City of London 001A (E01000001) recorded 2 incidents for crime type drugs. "
                    "This represented 16.7% of all incidents in the area and ranked #2 among crime types for that "
                    "area-month."
                ),
                "dataset_version_id": "dataset-v1",
            },
        },
        {
            "distance": 0.91,
            "entity": {
                "chunk_id": "area-cat-3",
                "chunk_type": "area_month_category",
                "reference_month": "2026-01",
                "lsoa_code": "E01000001",
                "crime_type": "shoplifting",
                "title": "2026-01 City of London 001A shoplifting",
                "content": (
                    "In 2026-01, area City of London 001A (E01000001) recorded 1 incidents for crime type "
                    "shoplifting. This represented 8.3% of all incidents in the area and ranked #3 among crime types "
                    "for that area-month."
                ),
                "dataset_version_id": "dataset-v1",
            },
        },
    ]
    pipeline = RagPipeline(
        FAKE_CONFIG,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(area_hits),
        generator=FakeGenerator(),
    )

    response = pipeline.run(
        RagQuery(
            query="Quais tipos de crime registrados em City of London 001A (E01000001)?",
            profile=AccessProfile.intel_user,
        )
    )

    assert response.answer.status == "answered"
    assert "foram identificados 3 tipos de crime registrados" in response.answer.text
    assert "- crime veicular: 3 incidente(s) [E1]" in response.answer.text
    assert "- drogas: 2 incidente(s) [E2]" in response.answer.text
    assert "- furto em comercio: 1 incidente(s) [E3]" in response.answer.text


def test_retrieval_diversifies_duplicate_hits_before_prompt_context():
    context = milvus_hits_to_context(
        [
            _duplicate_crime_hit("crime-1", "Westminster 2024-01 burglary A", score=0.95),
            _duplicate_crime_hit("crime-2", "Westminster 2024-01 burglary B", score=0.91),
            {
                "distance": 0.89,
                "entity": {
                    "chunk_id": "ranking-1",
                    "chunk_type": "area_month_top_crimes",
                    "reference_month": "2024-01",
                    "lsoa_code": "E01001234",
                    "crime_type": "burglary",
                    "title": "Westminster 2024-01 top crimes",
                    "content": "Top crimes were burglary and robbery.",
                    "dataset_version_id": "dataset-v1",
                },
            },
        ],
        AccessProfile.intel_user,
    )

    assert context[0].metadata["chunk_type"] == "area_month_category"
    assert context[1].metadata["chunk_type"] == "area_month_top_crimes"


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
        with (
            patch("urban_lens.api.services.rag_service.run_chat_query", return_value=mock_response),
            patch("urban_lens.governance.store.MetadataStore.record_request_audit"),
        ):
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
    assert "Responda inteiramente em portugues" in prompt
    assert "Nao misture idiomas" in prompt


def test_detect_question_language_keeps_english_queries_in_english():
    assert detect_question_language("What crime type was dominant in Westminster?") == "en"


def test_answer_shape_prefers_bulleted_listing_for_crime_type_queries():
    shape = infer_answer_shape("Quais tipos de crime foram registrados em E01000001?", "pt")

    assert "Liste os tipos de crime em bullets" in shape


def test_ollama_generator_uses_deterministic_options(monkeypatch):
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"response":"ok","prompt_eval_count":12,"eval_count":4}'

    def _fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("urban_lens.rag.generation.urllib.request.urlopen", _fake_urlopen)

    result = OllamaGenerator("http://localhost:11434").generate("prompt", "llama3")

    assert result.text == "ok"
    assert captured["timeout"] == 300
    assert captured["payload"]["options"] == {"temperature": 0, "seed": 42}
