"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database (Supabase pgvector)
    database_url: str

    # Groq API
    groq_api_key: str
    groq_model: str = "qwen/qwen3-32b"
    groq_max_tokens: int = 2048

    # Router model — used for query classification (smaller = faster + cheaper)
    # Uses the same Groq API key. Llama 3.1 8B is fast and good enough for routing.
    groq_router_model: str = "llama-3.1-8b-instant"

    # Embedding model (CPU inference for single queries)
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024

    # Retrieval settings
    similarity_threshold: float = 0.3

    # Strategy A (specific query): chunks per source type (independent retrieval)
    # Interviews and plans are searched separately to guarantee both appear
    top_k_specific_interviews: int = 3
    top_k_specific_plans: int = 3

    # Strategy B (general query): chunks per candidate per source type
    # e.g., 2 means up to 2 interview chunks + 2 plan chunks per candidate
    top_k_per_group: int = 2

    # Token budget for context (prevents 413 from Groq free tier)
    # System prompt ~500 tokens + user question ~50 + this = total input
    # Groq free tier: 6000 TPM, so keep context under ~4500
    max_context_tokens: int = 4500

    # App
    app_name: str = "AIPE"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()