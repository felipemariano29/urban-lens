"""SQLAlchemy models for governance tables exposed to the API."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from urban_lens.infrastructure.db import Base


class AccessPolicy(Base):
    __tablename__ = "access_policies"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    profile_name = Column(String, nullable=False)
    layer_scope = Column(String, nullable=False)
    dataset_scope = Column(String, nullable=False)
    allowed_actions = Column(JSONB, nullable=False)
    metadata_visibility = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False)


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"
    __table_args__ = {"schema": "governance"}

    retrieval_event_id = Column(UUID(as_uuid=True), primary_key=True)
    audit_id = Column(UUID(as_uuid=True), nullable=False)
    query = Column(Text, nullable=False)
    query_intent = Column(String, nullable=False)
    retrieval_method = Column(String, nullable=False)
    chunks_requested = Column(Integer, nullable=False)
    chunks_returned = Column(Integer, nullable=False)
    min_score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    mean_score = Column(Float, nullable=False)
    retrieval_latency_ms = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)


class ChunkRetrievalAudit(Base):
    __tablename__ = "chunk_retrieval_audit"
    __table_args__ = {"schema": "governance"}

    chunk_audit_id = Column(UUID(as_uuid=True), primary_key=True)
    retrieval_event_id = Column(UUID(as_uuid=True), nullable=False)
    chunk_id = Column(String, nullable=False)
    dataset_version_id = Column(UUID(as_uuid=True), nullable=False)
    rank = Column(Integer, nullable=False)
    relevance_score = Column(Float, nullable=False)
    crime_type = Column(String, nullable=False)
    reference_month = Column(String, nullable=False)
    included_in_response = Column(Boolean, nullable=False)
