"""Prometheus metrics middleware for request instrumentation."""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

# Request metrics
REQUEST_COUNT = Counter(
    "urban_lens_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status_code", "role", "plan"],
)

REQUEST_LATENCY = Histogram(
    "urban_lens_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route", "role"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUEST_IN_PROGRESS = Gauge(
    "urban_lens_http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "route"],
)

# RAG-specific metrics
RAG_QUERY_COUNT = Counter(
    "urban_lens_rag_queries_total",
    "Total RAG queries",
    ["query_type", "model", "status"],
)

RAG_QUERY_LATENCY = Histogram(
    "urban_lens_rag_query_duration_seconds",
    "RAG query latency in seconds",
    ["query_type", "model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

RAG_CHUNKS_RETRIEVED = Histogram(
    "urban_lens_rag_chunks_retrieved",
    "Number of chunks retrieved per RAG query",
    ["query_type"],
    buckets=(1, 2, 3, 5, 10, 15, 20),
)

# Governance metrics
API_KEY_AUTH_COUNT = Counter(
    "urban_lens_api_key_auth_total",
    "API key authentication attempts",
    ["status", "plan"],
)

RATE_LIMIT_HITS = Counter(
    "urban_lens_rate_limit_hits_total",
    "Rate limit violations",
    ["limit_type", "plan"],
)


def _extract_route_pattern(request: Request) -> str:
    """Extract the route pattern from a request, replacing path parameters."""
    if request.scope.get("route"):
        route = request.scope["route"]
        return route.path
    return request.url.path


def _extract_role(request: Request) -> str:
    """Extract role from request state."""
    profile = getattr(request.state, "user_profile", None)
    if profile:
        return profile.role
    return "unauthenticated"


def _extract_plan(request: Request) -> str:
    """Extract plan code from request state."""
    profile = getattr(request.state, "user_profile", None)
    if profile and profile.plan_code:
        return profile.plan_code
    return "none"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        route = _extract_route_pattern(request)

        REQUEST_IN_PROGRESS.labels(method=method, route=route).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            role = _extract_role(request)
            plan = _extract_plan(request)

            REQUEST_COUNT.labels(
                method=method,
                route=route,
                status_code=str(status_code),
                role=role,
                plan=plan,
            ).inc()

            REQUEST_LATENCY.labels(
                method=method,
                route=route,
                role=role,
            ).observe(duration)

            REQUEST_IN_PROGRESS.labels(method=method, route=route).dec()

        return response


def metrics_endpoint(request: Request) -> StarletteResponse:
    """Endpoint to expose Prometheus metrics."""
    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def record_rag_query(
    query_type: str,
    model: str,
    status: str,
    duration_seconds: float,
    chunks_count: int,
) -> None:
    """Record RAG query metrics. Call this from the RAG service."""
    RAG_QUERY_COUNT.labels(query_type=query_type, model=model, status=status).inc()
    RAG_QUERY_LATENCY.labels(query_type=query_type, model=model).observe(duration_seconds)
    RAG_CHUNKS_RETRIEVED.labels(query_type=query_type).observe(chunks_count)


def record_api_key_auth(status: str, plan: str = "none") -> None:
    """Record API key authentication attempt."""
    API_KEY_AUTH_COUNT.labels(status=status, plan=plan).inc()


def record_rate_limit_hit(limit_type: str, plan: str) -> None:
    """Record rate limit violation."""
    RATE_LIMIT_HITS.labels(limit_type=limit_type, plan=plan).inc()
