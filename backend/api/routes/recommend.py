"""
Recommendation endpoint — embedding similarity via orchestrator.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_orchestrator
from api.middleware.auth import get_current_user
from config.constants import IntentType
from schemas.recommendation import (
    Recommendation,
    RecommendRequest,
    RecommendResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    body: RecommendRequest,
    current_user: dict = Depends(get_current_user),
):
    """Return document recommendations based on embedding similarity.

    Accepts either *document_ids* (find similar docs) or *query*
    (semantic search) or both.
    """
    if not body.document_ids and not body.query:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of 'document_ids' or 'query'",
        )

    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised")

    context: Dict[str, Any] = {
        "user_id": current_user["user_id"],
        "intent": IntentType.RECOMMEND,
        "document_ids": body.document_ids or [],
        "top_k": body.top_k,
        "provider": body.provider,
    }

    try:
        result = await orchestrator.process(
            query=body.query or "Recommend similar documents",
            context=context,
        )

        raw = result.get("recommendations", []) if isinstance(result, dict) else []
        recommendations = [
            Recommendation(
                document_id=r.get("document_id", ""),
                title=r.get("title", ""),
                relevance_score=r.get("relevance_score", 0.0),
                reason=r.get("reason", ""),
            )
            for r in raw
        ]

        return RecommendResponse(
            recommendations=recommendations,
            query=body.query,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Recommendation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {exc}")
