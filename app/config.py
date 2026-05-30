from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App Configuration
    APP_NAME: str = "AI Research Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/research_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Upload Configuration
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = "pdf,txt,json,csv"

    # Embeddings Configuration
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Vector Store Configuration
    VECTOR_STORE_TYPE: str = "pinecone"
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "research-platform"

    # Security
    SECRET_KEY: str = "your_secret_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Logging
    LOG_FILE_PATH: str = "logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
