"""
FastAPI dependency injection module.

Provides lazy-initialized singleton instances for all major
services, injectable via FastAPI's Depends() system.
"""

from __future__ import annotations

import logging

from config.settings import get_settings
from api.middleware.auth import AuthManager
from database.connection import get_db as get_db_session  # alias for routes

logger = logging.getLogger(__name__)

# ── Module-level singletons (lazy) ─────────────────

_auth_manager: AuthManager | None = None
_model_registry = None
_qdrant_store = None
_shared_memory = None
_session_manager = None
_conversation_history = None
_ingestion_pipeline = None
_orchestrator = None
_event_bus = None


def get_auth_manager() -> AuthManager:
    """Get or create the AuthManager singleton"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def get_model_registry():
    """Get the initialized ModelRegistry"""
    global _model_registry
    if _model_registry is None:
        from models_layer.model_registry import ModelRegistry
        _model_registry = ModelRegistry()
    return _model_registry


def get_qdrant_store():
    """Get the initialized QdrantStore"""
    global _qdrant_store
    if _qdrant_store is None:
        from vectorstore.qdrant_store import QdrantStore
        _qdrant_store = QdrantStore()
    return _qdrant_store


def get_shared_memory():
    """Get the SharedMemory (Redis) instance"""
    global _shared_memory
    if _shared_memory is None:
        from memory.shared_memory import SharedMemory
        _shared_memory = SharedMemory()
    return _shared_memory


def get_session_manager():
    """Get the SessionManager instance"""
    global _session_manager
    if _session_manager is None:
        from memory.session_context import SessionManager
        _session_manager = SessionManager(get_shared_memory())
    return _session_manager


def get_conversation_history():
    """Get the ConversationHistory instance"""
    global _conversation_history
    if _conversation_history is None:
        from memory.conversation_history import ConversationHistory
        _conversation_history = ConversationHistory(get_shared_memory())
    return _conversation_history


def get_ingestion_pipeline():
    """Get the IngestionPipeline instance"""
    global _ingestion_pipeline
    if _ingestion_pipeline is None:
        from ingestion.pdf_extractor import PDFExtractor
        from ingestion.chunking import ChunkingEngine
        from ingestion.metadata_enricher import MetadataEnricher
        from ingestion.index_builder import IndexBuilder

        settings = get_settings()
        registry = get_model_registry()
        qdrant = get_qdrant_store()

        _ingestion_pipeline = __import__('ingestion.pipeline', fromlist=['IngestionPipeline']).IngestionPipeline(
            pdf_extractor=PDFExtractor(),
            chunking_engine=ChunkingEngine(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            ),
            metadata_enricher=MetadataEnricher(),
            index_builder=IndexBuilder(
                embedding_model=registry.get_embedding_model(),
                qdrant_store=qdrant,
            ),
        )
    return _ingestion_pipeline


def get_orchestrator():
    """Get the Orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        from orchestrator.intent_classifier import IntentClassifier
        from orchestrator.planner import TaskPlanner
        from orchestrator.dispatcher import AgentDispatcher
        from orchestrator.aggregator import ResponseAggregator
        from orchestrator.workflow import WorkflowEngine
        from orchestrator.orchestrator import Orchestrator
        from agents.registry import AgentRegistry

        registry = get_model_registry()

        intent_classifier = IntentClassifier(registry.get_classification_model())
        planner = TaskPlanner(intent_classifier)
        agent_registry = get_agent_registry()
        dispatcher = AgentDispatcher(agent_registry)
        aggregator = ResponseAggregator()
        workflow_engine = WorkflowEngine(dispatcher, aggregator)

        _orchestrator = Orchestrator(
            planner=planner,
            workflow_engine=workflow_engine,
            reasoning_factory=registry.get_reasoning_factory(),
        )
    return _orchestrator


# ── Agent Registry ──────────────────────────────────

_agent_registry = None


def get_agent_registry():
    """Get the AgentRegistry singleton"""
    global _agent_registry
    if _agent_registry is None:
        from agents.registry import AgentRegistry
        _agent_registry = AgentRegistry()
    return _agent_registry


def get_event_bus():
    """Get the EventBus singleton"""
    global _event_bus
    if _event_bus is None:
        from events.bus import EventBus
        _event_bus = EventBus()
    return _event_bus


async def initialize_all() -> None:
    """
    Initialize all services at startup.
    Called from the FastAPI lifespan handler.
    """
    settings = get_settings()
    logger.info("Initializing all services...")

    # 1. Model Registry
    logger.info("Loading ML models...")
    registry = get_model_registry()
    await registry.initialize()

    # 2. Qdrant
    logger.info("Initializing Qdrant...")
    qdrant = get_qdrant_store()
    await qdrant.initialize()

    # 3. Redis
    logger.info("Connecting to Redis...")
    _mem = get_shared_memory()

    # 4. Register agents
    logger.info("Registering agents...")
    agent_reg = get_agent_registry()

    from agents.retrieval.agent import RetrievalAgent
    from vectorstore.hybrid_search import HybridSearchEngine

    hybrid_engine = HybridSearchEngine(qdrant, registry.get_embedding_model())
    retrieval_agent = RetrievalAgent(qdrant, hybrid_engine, registry)
    agent_reg.register(retrieval_agent)

    # 5. Event bus
    logger.info("Setting up event bus...")
    bus = get_event_bus()
    from events.handlers import EventHandlerRegistry
    EventHandlerRegistry.register_default_handlers(bus)

    # 6. Warm up orchestrator
    _ = get_orchestrator()

    logger.info("All services initialized successfully!")


async def shutdown_all() -> None:
    """Shutdown all services gracefully."""
    logger.info("Shutting down services...")

    try:
        mem = get_shared_memory()
        await mem.close()
    except Exception as exc:
        logger.warning(f"Redis shutdown error: {exc}")

    try:
        registry = get_model_registry()
        await registry.shutdown()
    except Exception as exc:
        logger.warning(f"Model registry shutdown error: {exc}")

    logger.info("All services shut down.")
