from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.routes import health, upload, retrieval
from app.utils import setup_logger

settings = get_settings()
logger = setup_logger(__name__, settings.LOG_LEVEL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info("Application starting up")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    yield

    # Shutdown
    logger.info("Application shutting down")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI Research Platform Backend API",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include route modules
    app.include_router(health.router)
    app.include_router(upload.router)
    app.include_router(retrieval.router)

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    logger.info("Application configured successfully")
    return app
