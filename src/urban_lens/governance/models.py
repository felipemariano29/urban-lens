"""SQLAlchemy models for governance tables exposed to the API."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String
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
