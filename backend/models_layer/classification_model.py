"""
Rule-based classification model (placeholder for a future DistilBERT classifier).

Intent and domain classification are performed via keyword matching.
The module deliberately follows the ``ModelProvider`` lifecycle so it can
be swapped transparently once a proper model is trained.
"""

from __future__ import annotations

import logging
import re
from typing import Sequence

from config.constants import IntentType
from models_layer.base import ModelProvider

logger = logging.getLogger(__name__)

# ── Keyword → Intent Mapping ────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[IntentType, list[str]] = {
    IntentType.QUESTION: [
        "what", "why", "how", "when", "where", "who", "which",
        "explain", "describe", "define", "is", "are", "does", "do",
        "can", "could", "would", "should",
    ],
    IntentType.SUMMARIZE: [
        "summarize", "summary", "summarise", "overview", "brief",
        "tldr", "tl;dr", "recap", "abstract",
    ],
    IntentType.QUIZ: [
        "quiz", "test", "mcq", "multiple choice", "flashcard",
        "question me", "assess", "examination", "evaluate",
    ],
    IntentType.RECOMMEND: [
        "recommend", "similar", "related", "suggest", "like this",
        "more like", "alternatives", "comparable",
    ],
    IntentType.LEARN: [
        "learn", "roadmap", "path", "curriculum", "course",
        "study plan", "learning path", "tutorial", "guide",
    ],
    IntentType.COMPARE: [
        "compare", "difference", "differences", "versus", "vs",
        "contrast", "distinguish",
    ],
}

# ── Domain Keywords ─────────────────────────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "computer_science": [
        "algorithm", "data structure", "programming", "software",
        "code", "machine learning", "deep learning", "neural",
        "database", "api", "network", "computer",
    ],
    "mathematics": [
        "math", "theorem", "proof", "algebra", "calculus",
        "geometry", "equation", "integral", "derivative",
    ],
    "physics": [
        "physics", "quantum", "relativity", "force", "energy",
        "particle", "wave", "thermodynamics",
    ],
    "biology": [
        "biology", "cell", "gene", "protein", "dna", "evolution",
        "organism", "ecology", "anatomy",
    ],
    "chemistry": [
        "chemistry", "molecule", "reaction", "element", "compound",
        "organic", "inorganic", "bond",
    ],
    "general": [],  # fallback
}


class ClassificationModel(ModelProvider):
    """Keyword-based intent & domain classifier.

    This is a lightweight placeholder that will be replaced by a fine-tuned
    DistilBERT model once enough labelled data is available.
    """

    def __init__(self) -> None:
        self._loaded: bool = False
        # Pre-compile word-boundary patterns for faster matching.
        self._intent_patterns: dict[IntentType, list[re.Pattern[str]]] = {}
        self._domain_patterns: dict[str, list[re.Pattern[str]]] = {}
        logger.info("ClassificationModel created (rule-based).")

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return "rule-based-classifier-v1"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        if self._loaded:
            return
        self._intent_patterns = {
            intent: [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in kws]
            for intent, kws in _INTENT_KEYWORDS.items()
        }
        self._domain_patterns = {
            domain: [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in kws]
            for domain, kws in _DOMAIN_KEYWORDS.items()
        }
        self._loaded = True
        logger.info("ClassificationModel loaded (compiled %d intent groups).", len(self._intent_patterns))

    async def unload(self) -> None:
        self._intent_patterns = {}
        self._domain_patterns = {}
        self._loaded = False
        logger.info("ClassificationModel unloaded.")

    async def health_check(self) -> bool:
        if not self._loaded:
            return False
        try:
            intent, conf = await self.classify_intent("What is deep learning?")
            return intent is not None and conf > 0.0
        except Exception:
            logger.exception("ClassificationModel health-check failed.")
            return False

    # ── Public API ───────────────────────────────────────────────────────

    async def classify_intent(self, text: str) -> tuple[str, float]:
        """Classify user intent from free-form text.

        Returns
        -------
        tuple[str, float]
            ``(IntentType.value, confidence)`` where confidence ∈ (0, 1].
        """
        await self._ensure_loaded()

        if not text or not text.strip():
            return IntentType.UNKNOWN.value, 0.0

        scores = self._score_keywords(text, self._intent_patterns)

        if not scores:
            return IntentType.UNKNOWN.value, 0.3

        best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
        total_hits = sum(scores.values())
        confidence = min(scores[best_intent] / max(total_hits, 1), 1.0)

        # Boost confidence when the hit count is high.
        if scores[best_intent] >= 3:
            confidence = min(confidence + 0.15, 1.0)

        logger.debug(
            "Intent classified: text='%s…' → %s (%.2f)",
            text[:60], best_intent.value, confidence,
        )
        return best_intent.value, round(confidence, 4)

    async def classify_domain(self, text: str) -> tuple[str, float]:
        """Classify the academic / knowledge domain of the text.

        Returns
        -------
        tuple[str, float]
            ``(domain_label, confidence)``.
        """
        await self._ensure_loaded()

        if not text or not text.strip():
            return "general", 0.0

        scores = self._score_keywords(text, self._domain_patterns)

        if not scores:
            return "general", 0.3

        best_domain = max(scores, key=scores.get)  # type: ignore[arg-type]
        total_hits = sum(scores.values())
        confidence = min(scores[best_domain] / max(total_hits, 1), 1.0)

        logger.debug(
            "Domain classified: text='%s…' → %s (%.2f)",
            text[:60], best_domain, confidence,
        )
        return best_domain, round(confidence, 4)

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _score_keywords(
        text: str,
        pattern_groups: dict[str | IntentType, Sequence[re.Pattern[str]]],
    ) -> dict[str | IntentType, int]:
        """Count keyword hits for each category."""
        scores: dict[str | IntentType, int] = {}
        for category, patterns in pattern_groups.items():
            hits = sum(1 for p in patterns if p.search(text))
            if hits:
                scores[category] = hits
        return scores

    async def _ensure_loaded(self) -> None:
        if not self._loaded:
            await self.load()
