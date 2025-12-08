"""
FastAPI middleware for API key validation.

Security features:
- Validates API key header on all /v1/ endpoints
- Uses timing-safe comparison via APIKeyStorage
- Logs failed validation attempts (with partial key only)
- Allows bypass for health/status endpoints
- Backward compatible: if no keys configured, requests pass through
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from utils.api_key_storage import APIKeyStorage

logger = logging.getLogger(__name__)

# Endpoints that don't require API key authentication
EXEMPT_PATHS = {
    "/",
    "/health",
    "/healthz",
    "/auth/status",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API keys on incoming requests"""

    def __init__(self, app):
        super().__init__(app)
        self.storage = APIKeyStorage()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip exempt paths
        if path in EXEMPT_PATHS:
            return await call_next(request)

        # Only validate /v1/ API endpoints
        if not path.startswith("/v1/"):
            return await call_next(request)

        # Skip validation if no API keys are configured (backward compatible)
        if not self.storage.has_keys():
            return await call_next(request)

        # Extract API key from headers
        api_key = self._extract_api_key(request)

        if not api_key:
            logger.warning(f"API key validation failed: no key provided for {path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "message": "API key required. Provide Authorization: Bearer <key> or X-API-Key header.",
                        "type": "authentication_error",
                        "code": 401
                    }
                }
            )

        # Validate the key (timing-safe comparison happens in storage)
        key_id = self.storage.validate_key(api_key)
        if not key_id:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "message": "Invalid API key.",
                        "type": "authentication_error",
                        "code": 401
                    }
                }
            )

        # Store key_id in request state for potential audit logging
        request.state.api_key_id = key_id

        return await call_next(request)

    def _extract_api_key(self, request: Request) -> str | None:
        """Extract API key from request headers.

        Accepts API keys from:
        - Authorization: Bearer <key>
        - X-API-Key: <key>
        - x-api-key: <key> (Anthropic format used by LiteLLM)
        """
        # Check Authorization header first (Bearer token format)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            potential_key = auth_header[7:].strip()  # Remove "Bearer " prefix
            if potential_key:
                return potential_key

        # Check X-API-Key header as alternative (case-insensitive)
        x_api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if x_api_key:
            return x_api_key.strip()

        return None
