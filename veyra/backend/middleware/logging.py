"""
backend/middleware/logging.py
=============================
Logging middleware for FastAPI.
"""

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.operations.metrics import metrics
from backend.operations.monitoring import error_monitor

logger = logging.getLogger("veyra.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", "")
        if not request_id or len(request_id) > 128:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            metrics.increment("http_requests_failed")
            metrics.observe_ms("http_request", duration_ms)
            error_monitor.capture(
                exc,
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 3),
                },
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000.0
        metrics.increment("http_requests_total")
        metrics.observe_ms("http_request", duration_ms)
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 3),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
