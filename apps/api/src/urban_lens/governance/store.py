"""PostgreSQL-backed governance metadata operations."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from urban_lens.governance.contracts import (
    AccessRequestPayload,
    AuditEventPayload,
    ApiClientPayload,
    ApiKeyPayload,
    DatasetVersionPayload,
    GovernedUserPayload,
    ModelVersionPayload,
    PipelineRunPayload,
    RequestAuditPayload,
)


class MetadataStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn)

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    def register_dataset_version(self, payload: DatasetVersionPayload) -> str:
        dataset_version_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.dataset_versions (
                    id,
                    source_name,
                    layer,
                    logical_name,
                    version,
                    schema_version,
                    object_path,
                    row_count,
                    content_hash,
                    valid_from,
                    valid_to,
                    status,
                    metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (layer, logical_name, version, object_path) DO NOTHING
                """,
                (
                    dataset_version_id,
                    payload.source_name,
                    payload.layer,
                    payload.logical_name,
                    payload.version,
                    payload.schema_version,
                    payload.object_path,
                    payload.row_count,
                    payload.content_hash,
                    payload.valid_from,
                    payload.valid_to,
                    payload.status,
                    json.dumps(payload.metadata_json),
                ),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    """
                    SELECT id FROM governance.dataset_versions
                    WHERE layer = %s AND logical_name = %s AND version = %s AND object_path = %s
                    """,
                    (payload.layer, payload.logical_name, payload.version, payload.object_path),
                )
                row = cursor.fetchone()
                dataset_version_id = str(row[0])
            connection.commit()
        return dataset_version_id

    def list_dataset_versions(
        self,
        *,
        logical_name: str | None = None,
        layer: str | None = None,
        version_prefix: str | None = None,
        version_lte: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[object] = []

        if logical_name is not None:
            clauses.append("logical_name = %s")
            values.append(logical_name)
        if layer is not None:
            clauses.append("layer = %s")
            values.append(layer)
        if version_prefix is not None:
            clauses.append("version LIKE %s")
            values.append(f"{version_prefix}%")
        if version_lte is not None:
            clauses.append("version <= %s")
            values.append(version_lte)

        query = """
            SELECT id, layer, logical_name, version, object_path, created_at
            FROM governance.dataset_versions
        """
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY version, object_path, created_at"

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, values)
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "layer": row[1],
                "logical_name": row[2],
                "version": row[3],
                "object_path": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]

    def register_pipeline_run(self, payload: PipelineRunPayload) -> str:
        pipeline_run_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.pipeline_runs (
                    id,
                    pipeline_name,
                    run_type,
                    status,
                    triggered_by,
                    input_versions,
                    output_versions,
                    error_summary
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    pipeline_run_id,
                    payload.pipeline_name,
                    payload.run_type,
                    payload.status,
                    payload.triggered_by,
                    json.dumps(payload.input_versions),
                    json.dumps(payload.output_versions),
                    payload.error_summary,
                ),
            )
            connection.commit()
        return pipeline_run_id

    def finalize_pipeline_run(
        self,
        pipeline_run_id: str,
        status: str,
        output_versions: list[str],
        error_summary: str | None = None,
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE governance.pipeline_runs
                SET finished_at = NOW(),
                    status = %s,
                    output_versions = %s::jsonb,
                    error_summary = %s
                WHERE id = %s
                """,
                (status, json.dumps(output_versions), error_summary, pipeline_run_id),
            )
            connection.commit()

    def register_lineage(
        self,
        upstream_dataset_version_id: str,
        downstream_dataset_version_id: str,
        transformation_name: str,
        pipeline_run_id: str,
    ) -> str:
        lineage_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.lineage_edges (
                    id,
                    upstream_dataset_version_id,
                    downstream_dataset_version_id,
                    transformation_name,
                    pipeline_run_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (upstream_dataset_version_id, downstream_dataset_version_id, transformation_name) DO NOTHING
""",
                (
                    lineage_id,
                    upstream_dataset_version_id,
                    downstream_dataset_version_id,
                    transformation_name,
                    pipeline_run_id,
                ),
            )
            connection.commit()
        return lineage_id

    def register_audit_event(self, payload: AuditEventPayload) -> str:
        event_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.audit_events (
                    id,
                    event_type,
                    actor,
                    object_type,
                    object_id,
                    details_json
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    event_id,
                    payload.event_type,
                    payload.actor,
                    payload.object_type,
                    payload.object_id,
                    json.dumps(payload.details_json),
                ),
            )
            connection.commit()
        return event_id

    def register_model_version(self, payload: ModelVersionPayload) -> str:
        model_version_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.model_versions (
                    id,
                    model_name,
                    model_version,
                    target_name,
                    training_dataset_version_id,
                    scoring_dataset_version_id,
                    training_window_start,
                    training_window_end,
                    metrics_json,
                    artifact_uri,
                    status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (
                    model_version_id,
                    payload.model_name,
                    payload.model_version,
                    payload.target_name,
                    payload.training_dataset_version_id,
                    payload.scoring_dataset_version_id,
                    payload.training_window_start,
                    payload.training_window_end,
                    json.dumps(payload.metrics_json),
                    payload.artifact_uri,
                    payload.status,
                ),
            )
            connection.commit()
        return model_version_id

    def create_governed_user(self, payload: GovernedUserPayload) -> str:
        user_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.users (
                    id,
                    full_name,
                    email,
                    organization,
                    role,
                    status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    organization = EXCLUDED.organization,
                    role = EXCLUDED.role,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    user_id,
                    payload.full_name,
                    payload.email.lower(),
                    payload.organization,
                    payload.role,
                    payload.status,
                ),
            )
            row = cursor.fetchone()
            connection.commit()
        return str(row[0])

    def create_api_client(self, payload: ApiClientPayload) -> str:
        client_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.api_clients (
                    id,
                    user_id,
                    plan_id,
                    client_name,
                    status,
                    requests_per_minute_override,
                    requests_per_day_override
                )
                SELECT
                    %s,
                    %s,
                    sp.id,
                    %s,
                    %s,
                    %s,
                    %s
                FROM governance.service_plans sp
                WHERE sp.code = %s
                ON CONFLICT (user_id, client_name) DO UPDATE
                SET plan_id = EXCLUDED.plan_id,
                    status = EXCLUDED.status,
                    requests_per_minute_override = EXCLUDED.requests_per_minute_override,
                    requests_per_day_override = EXCLUDED.requests_per_day_override,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    client_id,
                    payload.user_id,
                    payload.client_name,
                    payload.status,
                    payload.requests_per_minute_override,
                    payload.requests_per_day_override,
                    payload.plan_code.upper(),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Unknown service plan code: {payload.plan_code}")
            connection.commit()
        return str(row[0])

    def issue_api_key(self, payload: ApiKeyPayload) -> str:
        api_key_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.api_keys (
                    id,
                    client_id,
                    key_prefix,
                    key_hash,
                    status,
                    expires_at,
                    metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    api_key_id,
                    payload.client_id,
                    payload.key_prefix,
                    payload.key_hash,
                    payload.status,
                    payload.expires_at,
                    json.dumps(payload.metadata_json),
                ),
            )
            connection.commit()
        return api_key_id

    def create_access_request(self, payload: AccessRequestPayload) -> str:
        access_request_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.access_requests (
                    id,
                    full_name,
                    email,
                    organization,
                    use_case,
                    requested_plan_code,
                    status,
                    metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    access_request_id,
                    payload.full_name,
                    payload.email.lower(),
                    payload.organization,
                    payload.use_case,
                    payload.requested_plan_code,
                    payload.status,
                    json.dumps(payload.metadata_json),
                ),
            )
            connection.commit()
        return access_request_id

    def get_service_plan_by_code(self, code: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, code, name, requests_per_minute, requests_per_day, max_top_k, allowed_models, metadata_json
                FROM governance.service_plans
                WHERE code = %s
                """,
                (code.upper(),),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "code": row[1],
            "name": row[2],
            "requests_per_minute": row[3],
            "requests_per_day": row[4],
            "max_top_k": row[5],
            "allowed_models": row[6],
            "metadata_json": row[7],
        }

    def get_api_key_record(self, key_prefix: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ak.id,
                    ak.client_id,
                    ak.key_prefix,
                    ak.key_hash,
                    ak.status,
                    ak.expires_at,
                    ak.last_used_at,
                    ak.metadata_json,
                    ac.user_id,
                    ac.client_name,
                    ac.status,
                    ac.requests_per_minute_override,
                    ac.requests_per_day_override,
                    u.email,
                    u.full_name,
                    u.role,
                    u.status,
                    sp.id,
                    sp.code,
                    sp.requests_per_minute,
                    sp.requests_per_day,
                    sp.max_top_k,
                    sp.allowed_models
                FROM governance.api_keys ak
                JOIN governance.api_clients ac ON ac.id = ak.client_id
                JOIN governance.users u ON u.id = ac.user_id
                JOIN governance.service_plans sp ON sp.id = ac.plan_id
                WHERE ak.key_prefix = %s
                """,
                (key_prefix,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "api_key_id": str(row[0]),
            "client_id": str(row[1]),
            "key_prefix": row[2],
            "key_hash": row[3],
            "api_key_status": row[4],
            "expires_at": row[5],
            "last_used_at": row[6],
            "api_key_metadata_json": row[7],
            "user_id": str(row[8]),
            "client_name": row[9],
            "client_status": row[10],
            "requests_per_minute_override": row[11],
            "requests_per_day_override": row[12],
            "email": row[13],
            "full_name": row[14],
            "role": row[15],
            "user_status": row[16],
            "plan_id": str(row[17]),
            "plan_code": row[18],
            "plan_requests_per_minute": row[19],
            "plan_requests_per_day": row[20],
            "plan_max_top_k": row[21],
            "allowed_models": row[22],
            "effective_requests_per_minute": row[11] if row[11] is not None else row[19],
            "effective_requests_per_day": row[12] if row[12] is not None else row[20],
        }

    def touch_api_key_usage(self, api_key_id: str, client_id: str) -> None:
        now = datetime.now(UTC)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE governance.api_keys
                SET last_used_at = %s
                WHERE id = %s
                """,
                (now, api_key_id),
            )
            cursor.execute(
                """
                UPDATE governance.api_clients
                SET last_used_at = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (now, client_id),
            )
            connection.commit()

    def count_client_requests(
        self,
        client_id: str,
        *,
        window_minutes: int | None = None,
        window_days: int | None = None,
    ) -> dict[str, int]:
        minute_count = 0
        day_count = 0
        minute_tokens = 0
        day_tokens = 0
        now = datetime.now(UTC)

        with self._connect() as connection, connection.cursor() as cursor:
            if window_minutes is not None:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(COALESCE((metadata_json->>'total_tokens')::int, 0)), 0)
                    FROM governance.request_audit
                    WHERE client_id = %s
                      AND completed_at >= %s
                    """,
                    (client_id, now.replace(microsecond=0) - timedelta(minutes=window_minutes)),
                )
                row = cursor.fetchone()
                minute_count = int(row[0]) if row else 0
                minute_tokens = int(row[1]) if row else 0

            if window_days is not None:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(COALESCE((metadata_json->>'total_tokens')::int, 0)), 0)
                    FROM governance.request_audit
                    WHERE client_id = %s
                      AND completed_at >= %s
                    """,
                    (client_id, now.replace(microsecond=0) - timedelta(days=window_days)),
                )
                row = cursor.fetchone()
                day_count = int(row[0]) if row else 0
                day_tokens = int(row[1]) if row else 0

        return {
            "minute_count": minute_count,
            "day_count": day_count,
            "minute_tokens": minute_tokens,
            "day_tokens": day_tokens,
        }

    def list_api_clients(
        self,
        *,
        user_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """List API clients with their plan and user information."""
        clauses: list[str] = []
        values: list[object] = []

        if user_id is not None:
            clauses.append("ac.user_id = %s")
            values.append(user_id)
        if not include_inactive:
            clauses.append("ac.status = 'active'")

        query = """
            SELECT
                ac.id,
                ac.user_id,
                ac.client_name,
                ac.status,
                ac.requests_per_minute_override,
                ac.requests_per_day_override,
                ac.last_used_at,
                ac.created_at,
                ac.updated_at,
                u.email,
                u.full_name,
                u.role,
                sp.code AS plan_code,
                sp.name AS plan_name,
                sp.requests_per_minute AS plan_requests_per_minute,
                sp.requests_per_day AS plan_requests_per_day,
                (SELECT COUNT(*) FROM governance.api_keys ak WHERE ak.client_id = ac.id AND ak.status = 'active') AS active_keys_count
            FROM governance.api_clients ac
            JOIN governance.users u ON u.id = ac.user_id
            JOIN governance.service_plans sp ON sp.id = ac.plan_id
        """
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ac.created_at DESC"

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, values)
            rows = cursor.fetchall()

        return [
            {
                "client_id": str(row[0]),
                "user_id": str(row[1]),
                "client_name": row[2],
                "status": row[3],
                "requests_per_minute_override": row[4],
                "requests_per_day_override": row[5],
                "last_used_at": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "user_email": row[9],
                "user_full_name": row[10],
                "user_role": row[11],
                "plan_code": row[12],
                "plan_name": row[13],
                "plan_requests_per_minute": row[14],
                "plan_requests_per_day": row[15],
                "active_keys_count": row[16],
            }
            for row in rows
        ]

    def list_api_keys(
        self,
        *,
        client_id: str | None = None,
        include_revoked: bool = False,
    ) -> list[dict[str, Any]]:
        """List API keys for a client or all keys."""
        clauses: list[str] = []
        values: list[object] = []

        if client_id is not None:
            clauses.append("ak.client_id = %s")
            values.append(client_id)
        if not include_revoked:
            clauses.append("ak.status != 'revoked'")

        query = """
            SELECT
                ak.id,
                ak.client_id,
                ak.key_prefix,
                ak.status,
                ak.expires_at,
                ak.issued_at,
                ak.last_used_at,
                ak.revoked_at,
                ak.metadata_json,
                ac.client_name,
                u.email AS user_email
            FROM governance.api_keys ak
            JOIN governance.api_clients ac ON ac.id = ak.client_id
            JOIN governance.users u ON u.id = ac.user_id
        """
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ak.issued_at DESC"

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, values)
            rows = cursor.fetchall()

        return [
            {
                "api_key_id": str(row[0]),
                "client_id": str(row[1]),
                "key_prefix": row[2],
                "status": row[3],
                "expires_at": row[4],
                "issued_at": row[5],
                "last_used_at": row[6],
                "revoked_at": row[7],
                "metadata_json": row[8],
                "client_name": row[9],
                "user_email": row[10],
            }
            for row in rows
        ]

    def revoke_api_key(self, api_key_id: str, *, reason: str | None = None) -> bool:
        """Revoke an API key. Returns True if the key was found and revoked."""
        now = datetime.now(UTC)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE governance.api_keys
                SET status = 'revoked',
                    revoked_at = %s,
                    metadata_json = metadata_json || %s::jsonb
                WHERE id = %s AND status = 'active'
                """,
                (
                    now,
                    json.dumps({"revocation_reason": reason or "manual_revocation"}),
                    api_key_id,
                ),
            )
            affected = cursor.rowcount
            connection.commit()
        return affected > 0

    def rotate_api_key(
        self,
        api_key_id: str,
        *,
        new_key_prefix: str,
        new_key_hash: str,
        expires_at: datetime | None = None,
    ) -> str | None:
        """Rotate an API key by revoking the old one and issuing a new one with same client.

        Returns the new API key ID if successful, None otherwise.
        """
        now = datetime.now(UTC)
        new_api_key_id = self._new_id()

        with self._connect() as connection, connection.cursor() as cursor:
            # Get the client_id from the old key
            cursor.execute(
                """
                SELECT client_id FROM governance.api_keys
                WHERE id = %s AND status = 'active'
                """,
                (api_key_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            client_id = str(row[0])

            # Revoke the old key
            cursor.execute(
                """
                UPDATE governance.api_keys
                SET status = 'revoked',
                    revoked_at = %s,
                    metadata_json = metadata_json || '{"revocation_reason": "key_rotation"}'::jsonb
                WHERE id = %s
                """,
                (now, api_key_id),
            )

            # Issue the new key
            cursor.execute(
                """
                INSERT INTO governance.api_keys (
                    id,
                    client_id,
                    key_prefix,
                    key_hash,
                    status,
                    expires_at,
                    metadata_json
                ) VALUES (%s, %s, %s, %s, 'active', %s, %s::jsonb)
                """,
                (
                    new_api_key_id,
                    client_id,
                    new_key_prefix,
                    new_key_hash,
                    expires_at,
                    json.dumps({"rotated_from": api_key_id}),
                ),
            )
            connection.commit()

        return new_api_key_id

    def get_api_key_by_id(self, api_key_id: str) -> dict[str, Any] | None:
        """Get API key details by ID."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ak.id,
                    ak.client_id,
                    ak.key_prefix,
                    ak.status,
                    ak.expires_at,
                    ak.issued_at,
                    ak.last_used_at,
                    ak.revoked_at,
                    ac.client_name,
                    u.email AS user_email,
                    u.id AS user_id
                FROM governance.api_keys ak
                JOIN governance.api_clients ac ON ac.id = ak.client_id
                JOIN governance.users u ON u.id = ac.user_id
                WHERE ak.id = %s
                """,
                (api_key_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "api_key_id": str(row[0]),
            "client_id": str(row[1]),
            "key_prefix": row[2],
            "status": row[3],
            "expires_at": row[4],
            "issued_at": row[5],
            "last_used_at": row[6],
            "revoked_at": row[7],
            "client_name": row[8],
            "user_email": row[9],
            "user_id": str(row[10]),
        }

    def record_request_audit(self, payload: RequestAuditPayload) -> str:
        request_audit_id = self._new_id()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.request_audit (
                    id,
                    request_id,
                    user_id,
                    client_id,
                    api_key_id,
                    plan_id,
                    route_path,
                    http_method,
                    response_status,
                    model_name,
                    latency_ms,
                    remote_ip,
                    user_agent,
                    filters_json,
                    metadata_json,
                    completed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    request_audit_id,
                    payload.request_id,
                    payload.user_id,
                    payload.client_id,
                    payload.api_key_id,
                    payload.plan_id,
                    payload.route_path,
                    payload.http_method,
                    payload.response_status,
                    payload.model_name,
                    payload.latency_ms,
                    payload.remote_ip,
                    payload.user_agent,
                    json.dumps(payload.filters_json),
                    json.dumps(payload.metadata_json),
                    payload.completed_at,
                ),
            )
            connection.commit()
        return request_audit_id
