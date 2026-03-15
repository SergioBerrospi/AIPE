"""AIPE — Análisis Inteligente de Propuestas Electorales.

FastAPI application for the RAG-based electoral analysis chat.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.models.schemas import HealthResponse
from app.routers import chat


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load the embedding model at startup so the first request is fast."""
    logger.info("Starting AIPE backend...")
    settings = get_settings()
    logger.info(f"LLM model: {settings.groq_model}")
    logger.info(f"Embedding model: {settings.embedding_model}")

    # Pre-load embedding model
    from app.services.embedder import get_model
    get_model()

    logger.info("AIPE backend ready")
    yield
    logger.info("Shutting down AIPE backend")


app = FastAPI(
    title="AIPE API",
    description="RAG-based analysis of Peruvian presidential candidates' proposals",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — reads FRONTEND_URL from environment for production
# ---------------------------------------------------------------------------
_frontend_url = os.getenv("FRONTEND_URL", "")
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]
if _frontend_url:
    CORS_ORIGINS.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router)


@app.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    return HealthResponse(
        model=settings.groq_model,
        embedding_model=settings.embedding_model,
    )