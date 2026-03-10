"""Embedding service using multilingual-e5-large for query encoding.

Runs on CPU — fine for single-query inference at request time.
Uses the "query: " prefix as required by the E5 model family.
"""

import logging
from sentence_transformers import SentenceTransformer
from app.config import get_settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (singleton)."""
    global _model
    if _model is None:
        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model, device="cpu")
        logger.info("Embedding model loaded successfully")
    return _model


def embed_query(text: str) -> list[float]:
    """Embed a user query with the required 'query: ' prefix.

    The E5 model family requires:
    - "query: " prefix for search queries
    - "passage: " prefix for documents (used during ingestion)
    """
    model = get_model()
    prefixed = f"query: {text}"
    embedding = model.encode(prefixed, normalize_embeddings=True)
    return embedding.tolist()