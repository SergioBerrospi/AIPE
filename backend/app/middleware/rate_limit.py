# =============================================================================
# app/middleware/rate_limit.py
# =============================================================================
# Simple in-memory rate limiter using slowapi.
# Protects /chat and /chat/stream from accidental abuse.
#
# Install: pip install slowapi
# =============================================================================

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Global limit: 30 requests/minute across ALL users (by IP).
# This is intentionally simple for MVP — no auth, no per-user tracking.
# Adjust as needed once you see real traffic patterns.

GLOBAL_RATE = "30/minute"

# ---------------------------------------------------------------------------
# Limiter setup
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[GLOBAL_RATE],
    storage_uri="memory://",  # In-memory, resets on restart. Fine for MVP.
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom 429 response in Spanish for AIPE users."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Demasiadas consultas. Por favor espera un momento antes de intentar de nuevo.",
            "detail": str(exc.detail),
            "retry_after_seconds": 60,
        },
    )