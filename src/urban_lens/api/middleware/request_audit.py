from __future__ import annotations

import logging
import time

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

        self._record_request(
            request=request,
            response=response,
            profile=profile,
            latency_ms=round((time.perf_counter() - started_at) * 1000, 1),
        )
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
            store = MetadataStore(AppConfig.from_env().postgres_dsn)
            store.record_request_audit(
                RequestAuditPayload(
                    request_id=get_correlation_id() or request.headers.get("X-Request-ID") or "unknown",
                    route_path=request.url.path,
                    http_method=request.method,
                    user_id=profile.user_id,
                    client_id=profile.client_id,
                    api_key_id=profile.api_key_id,
                    plan_id=None,
                    response_status=response.status_code,
                    latency_ms=latency_ms,
                    remote_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata_json={
                        "auth_type": profile.auth_type,
                        "plan_code": profile.plan_code,
                    },
                )
            )
        except Exception as exc:
            logger.warning("Failed to persist request audit: %s", exc)
