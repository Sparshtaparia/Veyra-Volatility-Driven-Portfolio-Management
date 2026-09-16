"""Minimal API-key authentication and response hardening."""

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ApiSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, api_prefix: str, api_key: str | None) -> None:
        super().__init__(app)
        self.api_prefix = api_prefix.rstrip("/")
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        protected = request.url.path.startswith(f"{self.api_prefix}/")
        if protected and self.api_key and request.method != "OPTIONS":
            supplied = request.headers.get("x-api-key", "")
            if not hmac.compare_digest(supplied, self.api_key):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response
