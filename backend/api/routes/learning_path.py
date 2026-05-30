"""
Learning-path endpoints — generate, retrieve, and update progress.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session, get_orchestrator, get_shared_memory
from api.middleware.auth import get_current_user
from config.constants import ConceptStatus, IntentType
from schemas.learning_path import (
    ConceptNode,
    LearningPathRequest,
    LearningPathResponse,
    ProgressUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/learning-path", tags=["learning-path"])

_LP_TTL = 86_400 * 7  # 7 days


# ── Generate ────────────────────────────────────────


@router.post("/generate", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED)
async def generate_learning_path(
    body: LearningPathRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a learning path from one or more documents."""
    user_id = current_user["user_id"]

    # Validate documents
    try:
        from database.models import Document
        from sqlalchemy import select

        result = await session.execute(
            select(Document).where(
                Document.id.in_([uuid.UUID(d) for d in body.document_ids]),
                Document.user_id == uuid.UUID(user_id),
            )
        )
        found = {doc.id for doc in result.scalars().all()}
        missing = set(body.document_ids) - found
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Documents not found: {', '.join(missing)}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Document validation skipped: %s", exc)

    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised")

    context: Dict[str, Any] = {
        "user_id": user_id,
        "intent": IntentType.LEARN,
        "document_ids": body.document_ids,
        "topic": body.topic,
        "depth": body.depth,
        "provider": body.provider,
    }

    try:
        result = await orchestrator.process(
            query=body.topic or "Generate a learning path",
            context=context,
        )

        path_id = str(uuid.uuid4())
        raw_concepts = result.get("concepts", []) if isinstance(result, dict) else []

        concepts = []
        for i, c in enumerate(raw_concepts):
            concepts.append(
                ConceptNode(
                    concept_id=c.get("concept_id", f"c_{i}"),
                    title=c.get("title", ""),
                    description=c.get("description", ""),
                    order=c.get("order", i),
                    status=ConceptStatus.AVAILABLE if i == 0 else ConceptStatus.LOCKED,
                    prerequisites=c.get("prerequisites", []),
                    resources=c.get("resources", []),
                    source_pages=c.get("source_pages", []),
                )
            )

        response = LearningPathResponse(
            path_id=path_id,
            title=result.get("title", "Learning Path") if isinstance(result, dict) else "Learning Path",
            document_ids=body.document_ids,
            concepts=concepts,
            depth=body.depth,
            total_concepts=len(concepts),
        )

        # Cache in Redis
        mem = get_shared_memory()
        await mem.set_json(f"learning_path:{path_id}", response.model_dump(), ttl=_LP_TTL)

        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Learning path generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Learning path generation failed: {exc}")


# ── Retrieve ────────────────────────────────────────


@router.get("/{path_id}", response_model=LearningPathResponse)
async def get_learning_path(
    path_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a previously generated learning path."""
    mem = get_shared_memory()
    data = await mem.get_json(f"learning_path:{path_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Learning path not found or expired")
    return LearningPathResponse(**data)


# ── Progress ────────────────────────────────────────


@router.put("/{path_id}/progress")
async def update_progress(
    path_id: str,
    body: ProgressUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Mark a concept as completed / available / locked."""
    mem = get_shared_memory()
    data = await mem.get_json(f"learning_path:{path_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Learning path not found or expired")

    path = LearningPathResponse(**data)
    updated = False

    for concept in path.concepts:
        if concept.concept_id == body.concept_id:
            concept.status = body.status
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Concept '{body.concept_id}' not found")

    # Auto-unlock next concepts when a prerequisite is completed
    if body.status == ConceptStatus.COMPLETED:
        completed_ids = {c.concept_id for c in path.concepts if c.status == ConceptStatus.COMPLETED}
        for concept in path.concepts:
            if concept.status == ConceptStatus.LOCKED:
                if all(p in completed_ids for p in concept.prerequisites):
                    concept.status = ConceptStatus.AVAILABLE

    await mem.set_json(f"learning_path:{path_id}", path.model_dump(), ttl=_LP_TTL)

    return {"status": "updated", "path_id": path_id, "concept_id": body.concept_id}
