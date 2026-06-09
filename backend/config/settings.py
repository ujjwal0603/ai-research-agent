"""
Application settings for AI Research Agent Platform V2.

Uses pydantic-settings for type-safe configuration management.
All settings loaded from .env file and overridable via environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration — all environment variables"""

    # ── App ──────────────────────────────────────────
    APP_NAME: str = "AI Research Agent Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development / staging / production

    # ── Logging ──────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # text (dev) / json (production)

    # ── Server ───────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database (SQLite for local dev, PostgreSQL for production) ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./research_agent.db"

    # ── Redis ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ───────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_IN_MEMORY: bool = True  # Use in-memory Qdrant for local dev
    QDRANT_URL: str = ""  # Full URL for Qdrant Cloud (overrides host+port)

    # ── Database Pool ───────────────────────────────
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # ── Gemini API ───────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── OpenAI API ───────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── LLM Default Provider ────────────────────────
    DEFAULT_LLM_PROVIDER: str = "auto"  # "gemini", "openai", "auto"

    # ── Embedding Model ─────────────────────────────
    EMBEDDING_MODEL: str = "paraphrase-MiniLM-L3-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── Reranking Model ─────────────────────────────
    RERANKING_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── File Upload ─────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Text Chunking ───────────────────────────────
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # ── Retrieval ───────────────────────────────────
    TOP_K: int = 5

    # ── Authentication (JWT) ────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-secrets-token-urlsafe"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton)"""
    return Settings()
