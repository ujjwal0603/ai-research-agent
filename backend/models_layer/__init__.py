"""
Models Layer — unified model management for the AI Research Agent Platform V2.

Provides embedding, classification, reranking, and reasoning model abstractions
with lazy loading, health checks, and a central registry.
"""

from __future__ import annotations

from models_layer.base import ModelProvider
from models_layer.embedding_model import EmbeddingModel
from models_layer.classification_model import ClassificationModel
from models_layer.reranking_model import RerankingModel
from models_layer.model_registry import ModelRegistry
from models_layer.reasoning import (
    ReasoningModel,
    GeminiProvider,
    OpenAIProvider,
    ReasoningModelFactory,
)

__all__ = [
    "ModelProvider",
    "EmbeddingModel",
    "ClassificationModel",
    "RerankingModel",
    "ModelRegistry",
    "ReasoningModel",
    "GeminiProvider",
    "OpenAIProvider",
    "ReasoningModelFactory",
]
