"""
Intent classifier for routing user queries to the appropriate agent pipeline.

Uses the classification model (rule-based in Phase 1, DistilBERT in Phase 4)
to determine user intent and route queries accordingly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config.constants import IntentType

if TYPE_CHECKING:
    from models_layer.classification_model import ClassificationModel

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies user intent from natural language queries"""

    def __init__(self, classification_model: ClassificationModel) -> None:
        self._model = classification_model

    async def classify(self, query: str) -> tuple[IntentType, float]:
        """
        Classify the intent of a user query.

        Returns:
            Tuple of (IntentType, confidence_score)
        """
        intent_str, confidence = await self._model.classify_intent(query)

        try:
            intent = IntentType(intent_str)
        except ValueError:
            logger.warning(f"Unknown intent '{intent_str}', defaulting to QUESTION")
            intent = IntentType.QUESTION
            confidence = 0.5

        logger.info(f"Classified intent: {intent.value} (confidence: {confidence:.2f})")
        return intent, confidence
