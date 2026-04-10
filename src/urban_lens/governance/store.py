"""PostgreSQL-backed governance metadata operations."""

from __future__ import annotations

import json
import uuid
from typing import Any

from urban_lens.governance.contracts import (
    AuditEventPayload,
    ChunkRetrievalAuditPayload,
    DatasetVersionPayload,
    ModelVersionPayload,
    PipelineRunPayload,
    RetrievalEventPayload,
)


class MetadataStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn)

    def register_dataset_version(self, payload: DatasetVersionPayload) -> str:
        dataset_version_id = str(uuid.uuid4())
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
        pipeline_run_id = str(uuid.uuid4())
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
        lineage_id = str(uuid.uuid4())
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
        event_id = str(uuid.uuid4())
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
        model_version_id = str(uuid.uuid4())
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

    def record_retrieval_event(self, payload: RetrievalEventPayload) -> str:
        retrieval_event_id = str(uuid.uuid4())
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.retrieval_events (
                    retrieval_event_id,
                    audit_id,
                    query,
                    query_intent,
                    retrieval_method,
                    chunks_requested,
                    chunks_returned,
                    min_score,
                    max_score,
                    mean_score,
                    retrieval_latency_ms,
                    status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    retrieval_event_id,
                    payload.audit_id,
                    payload.query,
                    payload.query_intent,
                    payload.retrieval_method,
                    payload.chunks_requested,
                    payload.chunks_returned,
                    payload.min_score,
                    payload.max_score,
                    payload.mean_score,
                    payload.retrieval_latency_ms,
                    payload.status,
                ),
            )
            connection.commit()
        return retrieval_event_id

    def record_chunk_retrieval(self, payload: ChunkRetrievalAuditPayload) -> str:
        chunk_audit_id = str(uuid.uuid4())
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO governance.chunk_retrieval_audit (
                    chunk_audit_id,
                    retrieval_event_id,
                    chunk_id,
                    dataset_version_id,
                    rank,
                    relevance_score,
                    crime_type,
                    reference_month,
                    included_in_response
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chunk_audit_id,
                    payload.retrieval_event_id,
                    payload.chunk_id,
                    payload.dataset_version_id,
                    payload.rank,
                    payload.relevance_score,
                    payload.crime_type,
                    payload.reference_month,
                    payload.included_in_response,
                ),
            )
            connection.commit()
        return chunk_audit_id
