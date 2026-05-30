"""
CORS middleware setup.

Reads allowed origins from application settings and attaches
``CORSMiddleware`` to the FastAPI application.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI) -> None:
    """Attach CORSMiddleware to *app* using settings from config.

    This should be called once during application setup, before
    any routes are registered.
    """
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(
        "CORS configured — origins=%s",
        settings.CORS_ORIGINS,
    )
