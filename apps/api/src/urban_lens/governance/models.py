"""SQLAlchemy models for governance tables exposed to the API."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
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


class ServicePlan(Base):
    __tablename__ = "service_plans"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    requests_per_minute = Column(Integer, nullable=False)
    requests_per_day = Column(Integer, nullable=False)
    max_top_k = Column(Integer, nullable=False)
    allowed_models = Column(JSONB, nullable=False)
    metadata_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False)


class GovernedUser(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    organization = Column(String, nullable=True)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ApiClient(Base):
    __tablename__ = "api_clients"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("governance.users.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("governance.service_plans.id"), nullable=False)
    client_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    requests_per_minute_override = Column(Integer, nullable=True)
    requests_per_day_override = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("governance.api_clients.id"), nullable=False)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    status = Column(String, nullable=False)
    issued_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSONB, nullable=False)


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    organization = Column(String, nullable=True)
    use_case = Column(String, nullable=False)
    requested_plan_code = Column(String, nullable=False)
    status = Column(String, nullable=False)
    metadata_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class RequestAudit(Base):
    __tablename__ = "request_audit"
    __table_args__ = {"schema": "governance"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    request_id = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("governance.users.id"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("governance.api_clients.id"), nullable=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("governance.api_keys.id"), nullable=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("governance.service_plans.id"), nullable=True)
    route_path = Column(String, nullable=False)
    http_method = Column(String, nullable=False)
    response_status = Column(Integer, nullable=True)
    model_name = Column(String, nullable=True)
    latency_ms = Column(Float, nullable=True)
    remote_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    filters_json = Column(JSONB, nullable=False)
    metadata_json = Column(JSONB, nullable=False)
    requested_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
