"""
Quiz generation, retrieval, and submission endpoints.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session, get_orchestrator, get_shared_memory
from api.middleware.auth import get_current_user
from config.constants import IntentType
from schemas.quiz import (
    QuizQuestion,
    QuizRequest,
    QuizResponse,
    QuizResult,
    QuizSubmission,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quiz", tags=["quiz"])

# Quiz TTL in Redis (24 hours)
_QUIZ_TTL = 86_400


# ── Generate quiz ───────────────────────────────────


@router.post("/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    body: QuizRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Generate a quiz from one or more documents."""
    user_id = current_user["user_id"]

    # Validate document ownership
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
        "intent": IntentType.QUIZ,
        "document_ids": body.document_ids,
        "quiz_type": body.quiz_type,
        "num_questions": body.num_questions,
        "difficulty": body.difficulty,
        "provider": body.provider,
    }

    try:
        result = await orchestrator.process(
            query=f"Generate {body.num_questions} {body.quiz_type} questions",
            context=context,
        )

        quiz_id = str(uuid.uuid4())
        raw_questions = result.get("questions", []) if isinstance(result, dict) else []

        questions = []
        for i, q in enumerate(raw_questions):
            questions.append(
                QuizQuestion(
                    question_id=q.get("question_id", f"q_{i}"),
                    question=q.get("question", ""),
                    options=q.get("options", []),
                    correct_answer=q.get("correct_answer", ""),
                    explanation=q.get("explanation", ""),
                    difficulty=q.get("difficulty", body.difficulty),
                    source_page=q.get("source_page"),
                )
            )

        response = QuizResponse(
            quiz_id=quiz_id,
            title=result.get("title", "Generated Quiz") if isinstance(result, dict) else "Generated Quiz",
            document_ids=body.document_ids,
            questions=questions,
            quiz_type=body.quiz_type,
            difficulty=body.difficulty,
        )

        # Cache in Redis for later retrieval / submission
        mem = get_shared_memory()
        await mem.set_json(
            f"quiz:{quiz_id}",
            response.model_dump(),
            ttl=_QUIZ_TTL,
        )

        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Quiz generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {exc}")


# ── Get quiz ────────────────────────────────────────


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a previously generated quiz by ID."""
    mem = get_shared_memory()
    data = await mem.get_json(f"quiz:{quiz_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Quiz not found or expired")
    return QuizResponse(**data)


# ── Submit answers ──────────────────────────────────


@router.post("/{quiz_id}/submit", response_model=QuizResult)
async def submit_quiz(
    quiz_id: str,
    submission: QuizSubmission,
    current_user: dict = Depends(get_current_user),
):
    """Submit quiz answers and receive a graded result."""
    mem = get_shared_memory()
    data = await mem.get_json(f"quiz:{quiz_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Quiz not found or expired")

    quiz = QuizResponse(**data)
    correct = 0
    details = []

    for q in quiz.questions:
        user_answer = submission.answers.get(q.question_id, "")
        is_correct = user_answer.strip().lower() == q.correct_answer.strip().lower()
        if is_correct:
            correct += 1
        details.append({
            "question_id": q.question_id,
            "user_answer": user_answer,
            "correct_answer": q.correct_answer,
            "is_correct": str(is_correct),
            "explanation": q.explanation,
        })

    total = len(quiz.questions)
    score = correct / total if total > 0 else 0.0

    return QuizResult(
        quiz_id=quiz_id,
        score=round(score, 4),
        correct=correct,
        total=total,
        details=details,
    )
