"""API endpoint and RBAC tests."""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime, timedelta
from typing import Generator
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

_JWT_SECRET = "test-secret-32-bytes-long-padded!"
_JWT_ALGO = "HS256"


def _token(role: str, **extra) -> str:
    return pyjwt.encode({"role": role, "sub": "tester", **extra}, _JWT_SECRET, algorithm=_JWT_ALGO)


def _auth(role: str, **extra) -> dict:
    return {"Authorization": f"Bearer {_token(role, **extra)}"}


def _api_key_header(key: str = "test-svc-key") -> dict:
    return {"X-API-Key": key}


def _governed_api_key() -> str:
    return "ul_abc123def456_secret-token-value"


def _governed_api_key_record(**overrides) -> dict:
    api_key = _governed_api_key()
    record = {
        "api_key_id": "api-key-1",
        "client_id": "client-1",
        "user_id": "user-1",
        "plan_id": "plan-1",
        "key_prefix": "abc123def456",
        "key_hash": hashlib.sha256(api_key.encode("utf-8")).hexdigest(),
        "api_key_status": "active",
        "client_status": "active",
        "user_status": "active",
        "expires_at": datetime.now(UTC) + timedelta(days=7),
        "email": "viewer@urbanlens.local",
        "role": "viewer",
        "requests_per_minute_override": None,
        "requests_per_day_override": None,
        "plan_code": "FREE",
        "plan_requests_per_minute": 30,
        "plan_requests_per_day": 500,
        "plan_max_top_k": 5,
        "effective_requests_per_minute": 30,
        "effective_requests_per_day": 500,
        "allowed_models": ["llama3", "phi3"],
    }
    record.update(overrides)
    return record


@pytest.fixture(autouse=True)
def _set_jwt_secret(monkeypatch):
    monkeypatch.setenv("URBAN_LENS_JWT_SECRET", _JWT_SECRET)


@pytest.fixture
def client(_set_jwt_secret) -> Generator:
    from urban_lens.api.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def client_with_svc_key(_set_jwt_secret, monkeypatch) -> Generator:
    monkeypatch.setenv("URBAN_LENS_INTERNAL_API_KEY", "test-svc-key")
    from urban_lens.api.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def all_services_healthy():
    with (
        patch("urban_lens.api.routers.health._check_postgres", return_value="ok"),
        patch("urban_lens.api.routers.health._check_ollama", return_value="ok"),
        patch("urban_lens.api.routers.health._check_milvus", return_value="ok"),
    ):
        yield


# ---------------------------------------------------------------------------
# /api/v1/health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_all_healthy_returns_200(self, client, all_services_healthy):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["dependencies"] == {
            "catalog": "ok",
            "rag_embedder": "ok",
            "rag_vector_store": "ok",
        }

    def test_degraded_returns_207(self, client):
        with (
            patch("urban_lens.api.routers.health._check_postgres", return_value="unavailable"),
            patch("urban_lens.api.routers.health._check_ollama", return_value="ok"),
            patch("urban_lens.api.routers.health._check_milvus", return_value="ok"),
        ):
            resp = client.get("/api/v1/health")
        assert resp.status_code == 207
        assert resp.json()["status"] == "degraded"

    def test_response_structure(self, client, all_services_healthy):
        """All expected top-level fields must be present."""
        resp = client.get("/api/v1/health")
        body = resp.json()
        assert "status" in body
        assert "version" in body
        assert "timestamp" in body
        assert "dependencies" in body
        assert set(body["dependencies"].keys()) == {"catalog", "rag_embedder", "rag_vector_store"}

    def test_timestamp_present(self, client, all_services_healthy):
        resp = client.get("/api/v1/health")
        assert "timestamp" in resp.json()

    def test_no_authentication_required(self, client, all_services_healthy):
        """Health is a public probe — no auth header should still return a response."""
        resp = client.get("/api/v1/health")
        assert resp.status_code in (200, 207)

    def test_all_dependencies_degraded_returns_207(self, client):
        with (
            patch("urban_lens.api.routers.health._check_postgres", return_value="unavailable"),
            patch("urban_lens.api.routers.health._check_ollama", return_value="unavailable"),
            patch("urban_lens.api.routers.health._check_milvus", return_value="unavailable"),
        ):
            resp = client.get("/api/v1/health")
        assert resp.status_code == 207
        body = resp.json()
        assert all(v == "unavailable" for v in body["dependencies"].values())


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_missing_credentials_returns_401(self, client):
        resp = client.post("/api/v1/query", json={"query": "test"})
        assert resp.status_code == 401

    def test_malformed_bearer_returns_401(self, client):
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"Authorization": "Token abc"},
        )
        assert resp.status_code == 401

    def test_invalid_jwt_returns_401(self, client):
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert resp.status_code == 401

    def test_expired_jwt_returns_401(self, client):
        expired_token = pyjwt.encode(
            {"role": "viewer", "sub": "tester", "exp": int(time.time()) - 60},
            _JWT_SECRET,
            algorithm=_JWT_ALGO,
        )
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_jwt_missing_role_field_returns_403(self, client):
        token = pyjwt.encode({"sub": "tester"}, _JWT_SECRET, algorithm=_JWT_ALGO)
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_unknown_role_returns_403(self, client):
        token = pyjwt.encode({"role": "superuser"}, _JWT_SECRET, algorithm=_JWT_ALGO)
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_invalid_api_key_returns_401(self, client, monkeypatch):
        monkeypatch.setenv("URBAN_LENS_INTERNAL_API_KEY", "correct-key")
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_valid_api_key_grants_internal_service(self, client_with_svc_key):
        mock_hits = [{"id": "c1", "score": 0.9, "content": "text", "metadata": {}}]
        with patch("urban_lens.api.services.rag_service.run_query", return_value=mock_hits):
            resp = client_with_svc_key.post(
                "/api/v1/query",
                json={"query": "test"},
                headers=_api_key_header(),
            )
        assert resp.status_code == 200

    def test_api_key_takes_precedence_over_jwt(self, client_with_svc_key):
        """When both headers are present, API Key wins."""
        mock_hits = [{"id": "c1", "score": 0.9, "content": "text", "metadata": {}}]
        with patch("urban_lens.api.services.rag_service.run_query", return_value=mock_hits):
            resp = client_with_svc_key.post(
                "/api/v1/query",
                json={"query": "test"},
                headers={**_auth("viewer"), **_api_key_header()},
            )
        assert resp.status_code == 200

    def test_valid_governed_api_key_grants_authenticated_access(self, client):
        mock_hits = [{"id": "c1", "score": 0.9, "content": "text", "metadata": {}}]
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=_governed_api_key_record()),
            patch("urban_lens.governance.store.MetadataStore.count_client_requests", return_value={"minute_count": 0, "day_count": 0}),
            patch("urban_lens.governance.store.MetadataStore.touch_api_key_usage"),
            patch("urban_lens.api.services.rag_service.run_query", return_value=mock_hits),
        ):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test"},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 200

    def test_expired_governed_api_key_returns_401(self, client):
        expired_record = _governed_api_key_record(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        with patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=expired_record):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test"},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 401

    def test_malformed_governed_api_key_returns_401(self, client):
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers=_api_key_header("invalid-key-format"),
        )
        assert resp.status_code == 401

    def test_authenticated_request_is_audited(self, client):
        mock_hits = [{"id": "c1", "score": 0.9, "content": "text", "metadata": {}}]
        with (
            patch("urban_lens.api.services.rag_service.run_query", return_value=mock_hits),
            patch("urban_lens.governance.store.MetadataStore.record_request_audit") as record_request_audit,
        ):
            resp = client.post("/api/v1/query", json={"query": "test"}, headers=_auth("viewer"))
        assert resp.status_code == 200
        assert record_request_audit.called

    def test_governed_api_key_rate_limit_returns_429(self, client):
        governed_record = _governed_api_key_record(effective_requests_per_minute=2)
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=governed_record),
            patch("urban_lens.governance.store.MetadataStore.count_client_requests", return_value={"minute_count": 2, "day_count": 2}),
        ):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test"},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 429
        assert "last minute" in resp.json()["message"]

    def test_governed_api_key_daily_quota_returns_429(self, client):
        governed_record = _governed_api_key_record(
            effective_requests_per_minute=30,
            effective_requests_per_day=10,
        )
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=governed_record),
            patch(
                "urban_lens.governance.store.MetadataStore.count_client_requests",
                return_value={"minute_count": 1, "day_count": 10},
            ),
        ):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test"},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 429
        assert "last day" in resp.json()["message"]

    def test_governed_query_rejects_top_k_above_plan_limit(self, client):
        governed_record = _governed_api_key_record(plan_max_top_k=3)
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=governed_record),
            patch("urban_lens.governance.store.MetadataStore.count_client_requests", return_value={"minute_count": 0, "day_count": 0}),
        ):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test", "top_k": 4},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 403
        assert "top_k=4" in resp.json()["message"]

    def test_governed_chat_rejects_disallowed_model(self, client):
        governed_record = _governed_api_key_record(allowed_models=["llama3"])
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=governed_record),
            patch("urban_lens.governance.store.MetadataStore.count_client_requests", return_value={"minute_count": 0, "day_count": 0}),
        ):
            resp = client.post(
                "/api/v1/chat/query",
                json={"query": "test", "model": "phi3"},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 403
        assert "phi3" in resp.json()["message"]

    def test_governed_chat_uses_default_model_when_plan_allows_it(self, client, monkeypatch):
        monkeypatch.setenv("URBAN_LENS_CHAT_MODEL", "llama3")
        governed_record = _governed_api_key_record(allowed_models=["llama3"])
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "answer": {"text": "ok", "status": "answered", "model": "llama3"},
            "evidences": [],
            "context": [],
            "profile": "intel_user",
            "fallback_reason": None,
            "timings_ms": {
                "embedding_ms": 1.0,
                "retrieval_ms": 1.0,
                "generation_ms": 1.0,
                "total_ms": 3.0,
            },
        }
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=governed_record),
            patch("urban_lens.governance.store.MetadataStore.count_client_requests", return_value={"minute_count": 0, "day_count": 0}),
            patch("urban_lens.governance.store.MetadataStore.touch_api_key_usage"),
            patch("urban_lens.api.services.rag_service.run_chat_query", return_value=mock_response) as run_chat_query,
        ):
            resp = client.post(
                "/api/v1/chat/query",
                json={"query": "test"},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 200
        assert run_chat_query.call_args.kwargs["model"] == "llama3"

    def test_governed_chat_request_is_audited_with_model_context(self, client):
        governed_record = _governed_api_key_record(
            role="intel_user",
            allowed_models=["llama3"],
        )
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "answer": {"text": "ok", "status": "answered", "model": "llama3"},
            "evidences": [],
            "context": [],
            "profile": "intel_user",
            "fallback_reason": None,
            "timings_ms": {
                "embedding_ms": 1.0,
                "retrieval_ms": 1.0,
                "generation_ms": 1.0,
                "total_ms": 3.0,
            },
        }
        with (
            patch("urban_lens.governance.store.MetadataStore.get_api_key_record", return_value=governed_record),
            patch("urban_lens.governance.store.MetadataStore.count_client_requests", return_value={"minute_count": 0, "day_count": 0}),
            patch("urban_lens.governance.store.MetadataStore.touch_api_key_usage"),
            patch("urban_lens.api.services.rag_service.run_chat_query", return_value=mock_response),
            patch("urban_lens.governance.store.MetadataStore.record_request_audit") as record_request_audit,
        ):
            resp = client.post(
                "/api/v1/chat/query",
                json={"query": "test", "model": "llama3", "top_k": 3, "filters": {"crime_type": "burglary"}},
                headers=_api_key_header(_governed_api_key()),
            )
        assert resp.status_code == 200
        payload = record_request_audit.call_args.args[0]
        assert payload.plan_id == "plan-1"
        assert payload.model_name == "llama3"
        assert payload.filters_json == {"crime_type": "burglary"}
        assert payload.metadata_json["top_k"] == 3


# ---------------------------------------------------------------------------
# Error envelope format
# ---------------------------------------------------------------------------


class TestErrorEnvelopes:
    def test_401_has_standardised_envelope(self, client):
        resp = client.post("/api/v1/query", json={"query": "test"})
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert "message" in body
        assert "details" in body

    def test_403_has_standardised_envelope(self, client):
        token = pyjwt.encode({"role": "superuser"}, _JWT_SECRET, algorithm=_JWT_ALGO)
        resp = client.post(
            "/api/v1/query",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert "error" in body
        assert "message" in body
        assert "details" in body

    def test_422_has_standardised_envelope(self, client):
        resp = client.post("/api/v1/query", json={}, headers=_auth("viewer"))
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "VALIDATION_ERROR"
        assert "message" in body
        assert "details" in body

    def test_502_has_standardised_envelope(self, client):
        with patch("urban_lens.api.services.rag_service.run_query", side_effect=RuntimeError("down")):
            resp = client.post("/api/v1/query", json={"query": "test"}, headers=_auth("viewer"))
        assert resp.status_code == 502
        body = resp.json()
        assert "error" in body
        assert "message" in body
        assert "details" in body

    def test_rbac_403_envelope_contains_role_info(self, client):
        """403 from RBAC should mention the denied role in the message."""
        resp = client.get("/api/v1/metadata/runs", headers=_auth("viewer"))
        assert resp.status_code == 403
        assert "viewer" in resp.json()["message"]


# ---------------------------------------------------------------------------
# Correlation ID (X-Request-ID)
# ---------------------------------------------------------------------------


class TestCorrelationId:
    def test_request_id_returned_in_response_headers(self, client, all_services_healthy):
        resp = client.get("/api/v1/health")
        assert "x-request-id" in resp.headers

    def test_custom_request_id_echoed_back(self, client, all_services_healthy):
        custom_id = "my-trace-id-abc123"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert resp.headers.get("x-request-id") == custom_id

    def test_auto_generated_id_is_uuid_like(self, client, all_services_healthy):
        resp = client.get("/api/v1/health")
        request_id = resp.headers.get("x-request-id", "")
        assert len(request_id) > 0
        assert len(request_id.split("-")) == 5


# ---------------------------------------------------------------------------
# POST /api/v1/query
# ---------------------------------------------------------------------------


class TestQuery:
    _MOCK_HIT = {
        "id": "chunk-001",
        "score": 0.87,
        "content": "3 burglaries in Westminster in January 2024.",
        "metadata": {
            "chunk_type": "area_month",
            "reference_month": "2024-01",
            "lsoa_code": "E01001234",
            "crime_type": "Burglary",
            "title": "Westminster 2024-01",
            "dataset_version_id": "v1",
        },
    }

    @pytest.mark.parametrize("role", ["viewer", "operator", "admin", "internal_service"])
    def test_all_roles_can_query(self, client_with_svc_key, role):
        headers = _api_key_header() if role == "internal_service" else _auth(role)
        with patch("urban_lens.api.services.rag_service.run_query", return_value=[self._MOCK_HIT]):
            resp = client_with_svc_key.post("/api/v1/query", json={"query": "burglary"}, headers=headers)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == "chunk-001"

    # -- top_k boundary values --

    def test_top_k_zero_returns_422(self, client):
        resp = client.post(
            "/api/v1/query",
            json={"query": "test", "top_k": 0},
            headers=_auth("viewer"),
        )
        assert resp.status_code == 422

    def test_top_k_min_boundary_returns_200(self, client):
        with patch("urban_lens.api.services.rag_service.run_query", return_value=[self._MOCK_HIT]):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test", "top_k": 1},
                headers=_auth("viewer"),
            )
        assert resp.status_code == 200

    def test_top_k_max_boundary_returns_200(self, client):
        with patch("urban_lens.api.services.rag_service.run_query", return_value=[self._MOCK_HIT]):
            resp = client.post(
                "/api/v1/query",
                json={"query": "test", "top_k": 20},
                headers=_auth("viewer"),
            )
        assert resp.status_code == 200

    def test_top_k_above_max_returns_422(self, client):
        resp = client.post(
            "/api/v1/query",
            json={"query": "test", "top_k": 999},
            headers=_auth("viewer"),
        )
        assert resp.status_code == 422
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_missing_query_field_returns_422(self, client):
        resp = client.post("/api/v1/query", json={}, headers=_auth("viewer"))
        assert resp.status_code == 422

    def test_rag_backend_error_returns_502(self, client):
        with patch("urban_lens.api.services.rag_service.run_query", side_effect=RuntimeError("down")):
            resp = client.post("/api/v1/query", json={"query": "test"}, headers=_auth("viewer"))
        assert resp.status_code == 502

    def test_filters_forwarded_to_service(self, client):
        captured: list = []

        def mock_run_query(query, top_k, filters):
            captured.append(filters)
            return []

        with patch("urban_lens.api.services.rag_service.run_query", side_effect=mock_run_query):
            client.post(
                "/api/v1/query",
                json={"query": "test", "filters": {"crime_type": "Burglary"}},
                headers=_auth("viewer"),
            )
        assert captured[0] == {"crime_type": "Burglary"}

    def test_empty_results_returns_200_with_empty_list(self, client):
        with patch("urban_lens.api.services.rag_service.run_query", return_value=[]):
            resp = client.post("/api/v1/query", json={"query": "test"}, headers=_auth("viewer"))
        assert resp.status_code == 200
        assert resp.json() == {"results": []}

    def test_response_structure(self, client):
        """Each result must have id, score, content and metadata."""
        with patch("urban_lens.api.services.rag_service.run_query", return_value=[self._MOCK_HIT]):
            resp = client.post("/api/v1/query", json={"query": "test"}, headers=_auth("viewer"))
        result = resp.json()["results"][0]
        assert "id" in result
        assert "score" in result
        assert "content" in result
        assert "metadata" in result

    def test_default_top_k_is_five(self, client):
        captured: list = []

        def mock_run_query(query, top_k, filters):
            captured.append(top_k)
            return []

        with patch("urban_lens.api.services.rag_service.run_query", side_effect=mock_run_query):
            client.post("/api/v1/query", json={"query": "test"}, headers=_auth("viewer"))
        assert captured[0] == 5


# ---------------------------------------------------------------------------
# GET /api/v1/metadata  (catalog)
# ---------------------------------------------------------------------------


class TestCatalogMetadata:
    _VIEWER_ENTRY = {"logical_name": "gold/rag/crime_chunks", "layer": "gold"}
    _OPERATOR_ENTRY = {**_VIEWER_ENTRY, "version": "2024-01"}
    _ADMIN_ENTRY = {
        **_OPERATOR_ENTRY,
        "id": "abc-123",
        "object_path": "gold/rag/crime_chunks/2024-01.parquet",
        "created_at": None,
    }

    @pytest.mark.parametrize(
        "role,expected_entry",
        [
            ("viewer", _VIEWER_ENTRY),
            ("operator", _OPERATOR_ENTRY),
            ("admin", _ADMIN_ENTRY),
        ],
    )
    def test_role_field_visibility(self, client, role, expected_entry):
        with patch("urban_lens.api.services.catalog_service.get_metadata", return_value=[expected_entry]):
            resp = client.get("/api/v1/metadata", headers=_auth(role))
        assert resp.status_code == 200
        assert resp.json()[0] == expected_entry

    def test_internal_service_sees_all_fields(self, client_with_svc_key):
        with patch("urban_lens.api.services.catalog_service.get_metadata", return_value=[self._ADMIN_ENTRY]):
            resp = client_with_svc_key.get("/api/v1/metadata", headers=_api_key_header())
        assert resp.status_code == 200
        assert resp.json()[0] == self._ADMIN_ENTRY

    def test_viewer_cannot_see_technical_fields(self, client):
        entry = {"logical_name": "gold/rag/crime_chunks", "layer": "gold"}
        with patch("urban_lens.api.services.catalog_service.get_metadata", return_value=[entry]):
            resp = client.get("/api/v1/metadata", headers=_auth("viewer"))
        data = resp.json()[0]
        assert "object_path" not in data
        assert "id" not in data
        assert "version" not in data

    def test_operator_cannot_see_technical_fields(self, client):
        """operator gets version but NOT id/object_path/created_at."""
        entry = {"logical_name": "gold/rag/crime_chunks", "layer": "gold", "version": "2024-01"}
        with patch("urban_lens.api.services.catalog_service.get_metadata", return_value=[entry]):
            resp = client.get("/api/v1/metadata", headers=_auth("operator"))
        data = resp.json()[0]
        assert "version" in data
        assert "id" not in data
        assert "object_path" not in data
        assert "created_at" not in data

    def test_catalog_backend_error_returns_502(self, client):
        with patch(
            "urban_lens.api.services.catalog_service.get_metadata",
            side_effect=RuntimeError("db down"),
        ):
            resp = client.get("/api/v1/metadata", headers=_auth("viewer"))
        assert resp.status_code == 502

    def test_source_filter_forwarded(self, client):
        captured: list = []

        def mock_get(profile, source):
            captured.append(source)
            return []

        with patch("urban_lens.api.services.catalog_service.get_metadata", side_effect=mock_get):
            client.get("/api/v1/metadata?source=gold/rag/crime_chunks", headers=_auth("viewer"))
        assert captured[0] == "gold/rag/crime_chunks"

    def test_empty_catalog_returns_200_with_empty_list(self, client):
        with patch("urban_lens.api.services.catalog_service.get_metadata", return_value=[]):
            resp = client.get("/api/v1/metadata", headers=_auth("viewer"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_no_source_filter_passes_none_to_service(self, client):
        captured: list = []

        def mock_get(profile, source):
            captured.append(source)
            return []

        with patch("urban_lens.api.services.catalog_service.get_metadata", side_effect=mock_get):
            client.get("/api/v1/metadata", headers=_auth("viewer"))
        assert captured[0] is None


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/runs  (MLflow — admin/internal_service only)
# ---------------------------------------------------------------------------


def _mock_mlflow_client(experiment_id="1", name="urban-lens-medallion", runs=None):
    mc = MagicMock()
    mc.get_experiment_by_name.return_value = MagicMock(experiment_id=experiment_id, name=name)
    mc.search_runs.return_value = runs or []
    return mc


class TestMLflowMetadata:
    @pytest.fixture(autouse=True)
    def _override_mlflow(self):
        from urban_lens.api.dependencies import get_mlflow_client
        from urban_lens.api.main import app

        mock_client = _mock_mlflow_client()
        app.dependency_overrides[get_mlflow_client] = lambda: mock_client
        yield mock_client
        app.dependency_overrides.pop(get_mlflow_client, None)

    @pytest.mark.parametrize("role", ["viewer", "operator"])
    def test_non_admin_roles_forbidden(self, client, role):
        resp = client.get("/api/v1/metadata/runs", headers=_auth(role))
        assert resp.status_code == 403

    def test_admin_can_list_runs(self, client):
        resp = client.get("/api/v1/metadata/runs", headers=_auth("admin"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_internal_service_api_key_can_list_runs(self, client, monkeypatch):
        monkeypatch.setenv("URBAN_LENS_INTERNAL_API_KEY", "svc-key")
        resp = client.get("/api/v1/metadata/runs", headers={"X-API-Key": "svc-key"})
        assert resp.status_code == 200

    def test_invalid_date_range_returns_422(self, client):
        resp = client.get(
            "/api/v1/metadata/runs?start_date=2024-12-31&end_date=2024-01-01",
            headers=_auth("admin"),
        )
        assert resp.status_code == 422

    def test_valid_date_range_returns_200(self, client):
        resp = client.get(
            "/api/v1/metadata/runs?start_date=2024-01-01&end_date=2024-12-31",
            headers=_auth("admin"),
        )
        assert resp.status_code == 200

    def test_start_date_only_returns_200(self, client):
        resp = client.get(
            "/api/v1/metadata/runs?start_date=2024-01-01",
            headers=_auth("admin"),
        )
        assert resp.status_code == 200

    def test_end_date_only_returns_200(self, client):
        resp = client.get(
            "/api/v1/metadata/runs?end_date=2024-12-31",
            headers=_auth("admin"),
        )
        assert resp.status_code == 200

    def test_unknown_experiment_returns_404(self, _override_mlflow, client):
        _override_mlflow.get_experiment_by_name.return_value = None
        resp = client.get(
            "/api/v1/metadata/runs?experiment_name=nonexistent",
            headers=_auth("admin"),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Internal routes
# ---------------------------------------------------------------------------


class TestInternalRoutes:
    @pytest.mark.parametrize("role", ["viewer", "operator"])
    def test_non_admin_forbidden(self, client, role):
        resp = client.get("/internal/status", headers=_auth(role))
        assert resp.status_code == 403

    def test_admin_allowed(self, client):
        resp = client.get("/internal/status", headers=_auth("admin"))
        assert resp.status_code == 200

    def test_internal_service_api_key_allowed(self, client_with_svc_key):
        resp = client_with_svc_key.get("/internal/status", headers=_api_key_header())
        assert resp.status_code == 200

    def test_not_in_openapi_schema(self, client):
        schema = client.get("/openapi.json").json()
        paths = schema.get("paths", {})
        assert "/internal/status" not in paths

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/internal/status")
        assert resp.status_code == 401
