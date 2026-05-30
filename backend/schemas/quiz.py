"""
Quiz / assessment Pydantic schemas.

Covers quiz generation request, individual questions with options,
the quiz response envelope, answer submission, and graded results.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config.constants import Difficulty, QuizType
from schemas.chat import SourceChunk

logger = logging.getLogger(__name__)


# ── Quiz Request ───────────────────────────────────


class QuizRequest(BaseModel):
    """Payload for quiz generation.

    Attributes:
        document_ids: Source documents to generate questions from.
        quiz_type: Question format (MCQ, flashcard, interview).
        count: Number of questions to generate (1-20).
        difficulty: Desired difficulty level.
        topics: Optional topic filters.
    """

    document_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Source document IDs",
    )
    quiz_type: QuizType = Field(
        ...,
        description="Question format",
    )
    count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of questions to generate",
    )
    difficulty: Difficulty = Field(
        default=Difficulty.MEDIUM,
        description="Desired difficulty level",
    )
    topics: Optional[List[str]] = Field(
        default=None,
        description="Optional topic filters",
    )


# ── Quiz Question ──────────────────────────────────


class QuizQuestion(BaseModel):
    """A single quiz question with optional answer choices.

    Attributes:
        question: The question text.
        options: Answer choices (MCQ only).
        correct_answer: The correct answer.
        explanation: Why the answer is correct.
        source_reference: Chunk the question was derived from.
        difficulty: Question difficulty level.
    """

    question: str = Field(..., description="Question text")
    options: Optional[List[str]] = Field(
        default=None,
        description="Answer options (MCQ only)",
    )
    correct_answer: str = Field(..., description="Correct answer")
    explanation: str = Field(
        ...,
        description="Explanation of the correct answer",
    )
    source_reference: SourceChunk = Field(
        ...,
        description="Source chunk the question was derived from",
    )
    difficulty: Difficulty = Field(..., description="Question difficulty")


# ── Quiz Response ──────────────────────────────────


class QuizResponse(BaseModel):
    """Full quiz returned after generation.

    Attributes:
        quiz_id: Unique quiz ID.
        quiz_type: Question format used.
        questions: Generated questions.
        document_ids: Source document IDs.
        created_at: Generation timestamp (UTC).
    """

    quiz_id: str = Field(..., description="Unique quiz ID")
    quiz_type: QuizType = Field(..., description="Question format")
    questions: List[QuizQuestion] = Field(
        ...,
        description="Generated questions",
    )
    document_ids: List[str] = Field(
        ...,
        description="Source document IDs",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Generation timestamp (UTC)",
    )


# ── Quiz Submission ────────────────────────────────


class QuizSubmission(BaseModel):
    """User's answers submitted for grading.

    Attributes:
        quiz_id: ID of the quiz being answered.
        answers: Mapping of question index (0-based) to user's answer.
    """

    quiz_id: str = Field(..., description="Quiz ID")
    answers: Dict[int, str] = Field(
        ...,
        description="Question index → user answer",
    )


# ── Quiz Result ────────────────────────────────────


class QuizResult(BaseModel):
    """Graded quiz result.

    Attributes:
        quiz_id: The quiz that was graded.
        score: Number of correct answers.
        total: Total number of questions.
        percentage: Score as a percentage (0–100).
        results: Per-question grading details.
    """

    quiz_id: str = Field(..., description="Quiz ID")
    score: int = Field(..., ge=0, description="Correct answers count")
    total: int = Field(..., ge=0, description="Total questions")
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score percentage (0–100)",
    )
    results: List[Dict[str, Any]] = Field(
        ...,
        description="Per-question grading details",
    )
