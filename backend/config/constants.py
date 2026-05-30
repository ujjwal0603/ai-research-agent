"""
Constants and enumerations for the AI Research Agent Platform V2.

Centralizes all fixed values, agent identifiers, intent types,
and configuration constants used across the system.
"""

from __future__ import annotations

from enum import Enum, auto


# ── Agent Identifiers ───────────────────────────────

class AgentID(str, Enum):
    """Unique identifiers for all registered agents"""
    RETRIEVAL = "retrieval_agent"
    SUMMARIZATION = "summarization_agent"
    CITATION = "citation_agent"
    RECOMMENDATION = "recommendation_agent"
    QUIZ = "quiz_agent"
    LEARNING_PATH = "learning_path_agent"


# ── Intent Types ────────────────────────────────────

class IntentType(str, Enum):
    """User intent classifications for orchestrator routing"""
    QUESTION = "question"
    SUMMARIZE = "summarize"
    QUIZ = "quiz"
    RECOMMEND = "recommend"
    LEARN = "learn"
    COMPARE = "compare"
    MULTI = "multi"
    UNKNOWN = "unknown"


# ── Agent Task Priority ─────────────────────────────

class Priority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# ── Document Processing Status ──────────────────────

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# ── Summary Types ───────────────────────────────────

class SummaryType(str, Enum):
    EXECUTIVE = "executive"
    SECTION = "section"
    BULLET = "bullet"
    ABSTRACT = "abstract"


# ── Quiz Types ──────────────────────────────────────

class QuizType(str, Enum):
    MCQ = "mcq"
    FLASHCARD = "flashcard"
    INTERVIEW = "interview"


# ── Difficulty Levels ───────────────────────────────

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ── Search Strategies ───────────────────────────────

class SearchStrategy(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


# ── LLM Providers ──────────────────────────────────

class LLMProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    AUTO = "auto"


# ── Learning Path Depth ─────────────────────────────

class LearningDepth(str, Enum):
    OVERVIEW = "overview"
    INTERMEDIATE = "intermediate"
    DEEP = "deep"


# ── Concept Status ──────────────────────────────────

class ConceptStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"


# ── Workflow Execution Patterns ─────────────────────

class WorkflowPattern(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ITERATIVE = "iterative"


# ── Event Types ─────────────────────────────────────

class EventType(str, Enum):
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_DELETED = "document.deleted"
    AGENT_TASK_STARTED = "agent.task.started"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    AGENT_TASK_FAILED = "agent.task.failed"
    CHAT_MESSAGE_RECEIVED = "chat.message.received"
    CHAT_RESPONSE_GENERATED = "chat.response.generated"


# ── Fixed Constants ─────────────────────────────────

# Embedding
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384

# Chunking
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50

# Retrieval
DEFAULT_TOP_K = 5
MAX_TOP_K = 20

# Qdrant collections
QDRANT_COLLECTION_CHUNKS = "document_chunks"
QDRANT_COLLECTION_CENTROIDS = "document_centroids"
QDRANT_COLLECTION_CONCEPTS = "concept_embeddings"

# API
API_VERSION = "2.0.0"
API_PREFIX = "/api"

# Auth
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
BCRYPT_ROUNDS = 12

# SSE
SSE_EVENT_START = "start"
SSE_EVENT_TOKEN = "token"
SSE_EVENT_SOURCES = "sources"
SSE_EVENT_DONE = "done"
SSE_EVENT_ERROR = "error"
