from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Request-ID"

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(HEADER_NAME) or str(uuid.uuid4())
        _correlation_id.set(request_id)
        response = await call_next(request)
        response.headers[HEADER_NAME] = request_id
        return response
