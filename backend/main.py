"""
AI Research Agent Platform V2 — FastAPI Entry Point

Multi-agent orchestrated RAG platform with:
- JWT authentication
- Qdrant vector store
- Gemini + OpenAI dual-provider LLM
- SSE streaming
- PostgreSQL + Redis
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config.settings import get_settings
from config.constants import API_VERSION
from api.middleware.cors import setup_cors
from api.dependencies import initialize_all, shutdown_all

# ── Logging Setup ────────────────────────────────────

_settings = get_settings()

try:
    from config.logging_config import setup_logging
    setup_logging(level=_settings.LOG_LEVEL, fmt=_settings.LOG_FORMAT)
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management"""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{API_VERSION}")
    logger.info(f"  Mode: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    logger.info("=" * 60)

    try:
        # Initialize database
        logger.info("Initializing database...")
        from database.connection import init_db
        await init_db()

        # Initialize all services
        await initialize_all()

        logger.info("=" * 60)
        logger.info("  ✅ Platform ready!")
        logger.info(f"  📡 API: http://{settings.HOST}:{settings.PORT}")
        logger.info(f"  📖 Docs: http://{settings.HOST}:{settings.PORT}/docs")
        logger.info("=" * 60)

    except Exception as exc:
        logger.exception(f"Startup failed: {exc}")
        logger.warning("Starting in degraded mode — some services may be unavailable")

    yield

    # Shutdown
    logger.info("Shutting down platform...")
    await shutdown_all()
    logger.info("Goodbye! 👋")


# ── App Factory ────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()

    is_production = settings.ENVIRONMENT == "production"

    app = FastAPI(
        title=settings.APP_NAME,
        version=API_VERSION,
        description="Multi-agent AI Research Platform with RAG, summarization, quiz generation, and learning paths",
        lifespan=lifespan,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
    )

    # CORS
    setup_cors(app)

    # Register routers
    from api.routes.health import router as health_router
    from api.routes.auth import router as auth_router
    from api.routes.documents import router as documents_router
    from api.routes.chat import router as chat_router
    from api.routes.summarize import router as summarize_router
    from api.routes.quiz import router as quiz_router
    from api.routes.recommend import router as recommend_router
    from api.routes.learning_path import router as learning_path_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(chat_router)
    app.include_router(summarize_router)
    app.include_router(quiz_router)
    app.include_router(recommend_router)
    app.include_router(learning_path_router)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": API_VERSION,
            "status": "running",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


# ── Application Instance ──────────────────────────

app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
