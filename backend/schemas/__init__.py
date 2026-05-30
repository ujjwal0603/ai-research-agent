"""
Schemas package for the AI Research Agent Platform V2.

Re-exports all Pydantic models so consumers can do:
    from schemas import ChatRequest, ChatResponse, ...
"""

from __future__ import annotations

# ── Common ──────────────────────────────────────────
from schemas.common import (
    AgentTrace,
    AgentTraceStep,
    ErrorResponse,
    PaginatedResponse,
    StatusResponse,
)

# ── Auth ────────────────────────────────────────────
from schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

# ── Documents ───────────────────────────────────────
from schemas.documents import (
    DocumentDetail,
    DocumentInfo,
    UploadResponse,
)

# ── Chat ────────────────────────────────────────────
from schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    SourceChunk,
    SSEEvent,
)

# ── Summary ─────────────────────────────────────────
from schemas.summary import (
    SummarizeRequest,
    SummaryResponse,
    SummarySection,
)

# ── Quiz ────────────────────────────────────────────
from schemas.quiz import (
    QuizQuestion,
    QuizRequest,
    QuizResponse,
    QuizResult,
    QuizSubmission,
)

# ── Recommendation ──────────────────────────────────
from schemas.recommendation import (
    Recommendation,
    RecommendRequest,
    RecommendResponse,
)

# ── Learning Path ───────────────────────────────────
from schemas.learning_path import (
    ConceptNode,
    LearningPathRequest,
    LearningPathResponse,
    ProgressUpdate,
)

# ── Agents ──────────────────────────────────────────
from schemas.agents import (
    AgentInfo,
    AgentMessage,
    AgentResult,
    AgentTask,
)

__all__ = [
    # common
    "PaginatedResponse",
    "ErrorResponse",
    "StatusResponse",
    "AgentTrace",
    "AgentTraceStep",
    # auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserResponse",
    # documents
    "UploadResponse",
    "DocumentInfo",
    "DocumentDetail",
    # chat
    "SourceChunk",
    "Citation",
    "ChatRequest",
    "ChatResponse",
    "SSEEvent",
    # summary
    "SummarizeRequest",
    "SummarySection",
    "SummaryResponse",
    # quiz
    "QuizRequest",
    "QuizQuestion",
    "QuizResponse",
    "QuizSubmission",
    "QuizResult",
    # recommendation
    "RecommendRequest",
    "Recommendation",
    "RecommendResponse",
    # learning path
    "LearningPathRequest",
    "ConceptNode",
    "LearningPathResponse",
    "ProgressUpdate",
    # agents
    "AgentMessage",
    "AgentTask",
    "AgentResult",
    "AgentInfo",
]
