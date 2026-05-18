from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from starlette.background import BackgroundTask, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.middleware.correlation import get_correlation_id
from urban_lens.core.settings import AppConfig
from urban_lens.governance import MetadataStore, RequestAuditPayload

logger = logging.getLogger(__name__)


class RequestAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)

        profile = getattr(request.state, "user_profile", None)
        if not isinstance(profile, UserProfile):
            return response

        background_task = BackgroundTask(
            self._record_request,
            request=request,
            response=response,
            profile=profile,
            latency_ms=round((time.perf_counter() - started_at) * 1000, 1),
        )
        if response.background is None:
            response.background = background_task
        elif isinstance(response.background, BackgroundTasks):
            response.background.add_task(
                self._record_request,
                request=request,
                response=response,
                profile=profile,
                latency_ms=round((time.perf_counter() - started_at) * 1000, 1),
            )
        else:
            tasks = BackgroundTasks()
            tasks.add_task(response.background.func, *response.background.args, **response.background.kwargs)
            tasks.add_task(
                self._record_request,
                request=request,
                response=response,
                profile=profile,
                latency_ms=round((time.perf_counter() - started_at) * 1000, 1),
            )
            response.background = tasks
        return response

    def _record_request(
        self,
        *,
        request: Request,
        response: Response,
        profile: UserProfile,
        latency_ms: float,
    ) -> None:
        try:
            audit_context = getattr(request.state, "audit_context", {})
            store = MetadataStore(AppConfig.from_env().postgres_dsn)
            store.record_request_audit(
                RequestAuditPayload(
                    request_id=get_correlation_id() or request.headers.get("X-Request-ID") or "unknown",
                    route_path=request.url.path,
                    http_method=request.method,
                    user_id=profile.user_id,
                    client_id=profile.client_id,
                    api_key_id=profile.api_key_id,
                    plan_id=profile.plan_id,
                    response_status=response.status_code,
                    model_name=audit_context.get("model_name"),
                    latency_ms=latency_ms,
                    remote_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    filters_json=audit_context.get("filters", {}),
                    metadata_json={
                        "auth_type": profile.auth_type,
                        "plan_code": profile.plan_code,
                        "top_k": audit_context.get("top_k"),
                        **(audit_context.get("token_usage") or {}),
                    },
                    completed_at=datetime.now(UTC),
                )
            )
        except Exception as exc:
            logger.warning("Failed to persist request audit: %s", exc)
