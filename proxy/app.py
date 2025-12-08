"""
FastAPI application initialization and configuration.
"""
import logging
from fastapi import FastAPI

from .middleware import log_requests_middleware
from .api_key_middleware import APIKeyMiddleware
from .endpoints import (
    health_router,
    models_router,
    auth_router,
    anthropic_messages_router,
    openai_chat_router,
    usage_router,
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="LLMux", version="1.0.0")

# Add middleware (order matters: last added executes first on request)
app.middleware("http")(log_requests_middleware)
app.add_middleware(APIKeyMiddleware)  # API key validation runs first

# Register routers
app.include_router(health_router)
app.include_router(models_router)
app.include_router(auth_router)
app.include_router(anthropic_messages_router)
app.include_router(openai_chat_router)
app.include_router(usage_router)

logger.debug("FastAPI application initialized with all routers and middleware")
