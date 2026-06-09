"""
Embedding model using feature-hashing (zero external dependencies).

This implementation uses the "hashing trick" to convert text into
fixed-dimension dense vectors using only numpy and hashlib.
It requires ZERO additional RAM, ZERO API calls, and ZERO downloads.

The vectors support cosine-similarity search in Qdrant and combined
with the existing BM25 sparse search, provide effective RAG retrieval.
Gemini still handles all the intelligent answer generation.
"""

from __future__ import annotations

import hashlib
import logging
import re

import numpy as np

from models_layer.base import ModelProvider

logger = logging.getLogger(__name__)

# ── Simple but effective tokenizer ───────────────────────────────────────

_WORD_RE = re.compile(r"[a-zA-Z0-9]+(?:'[a-z]+)?")

# Common English stop-words to down-weight (not remove — they still help)
_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into through during before after above below between "
    "out off over under again further then once here there when where "
    "why how all each every both few more most other some such no nor "
    "not only own same so than too very it its he she they them their "
    "this that these those i me my we our you your and but or if".split()
)


def _tokenize(text: str) -> list[str]:
    """Extract lowercase word tokens from text."""
    return [w.lower() for w in _WORD_RE.findall(text) if len(w) > 1]


class EmbeddingModel(ModelProvider):
    """Feature-hashing embedding model — zero RAM, zero API, zero downloads.

    Uses multiple hash functions to map words and bigrams into a
    fixed-dimension vector space. The resulting vectors support
    cosine similarity for nearest-neighbour search.
    """

    DIMENSION = 384
    _NUM_HASHES = 4        # Number of hash functions per token
    _BIGRAM_WEIGHT = 0.7   # Relative weight for bigram features
    _STOP_WEIGHT = 0.3     # Down-weight stop words (don't remove them)

    def __init__(self, model_name_or_path: str = "feature-hash-384") -> None:
        self._model_name = "feature-hash-384"
        self._dimension = self.DIMENSION
        self._loaded = False
        logger.info(
            "EmbeddingModel created (feature-hashing, dim=%d, zero RAM)",
            self._dimension,
        )

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        self._loaded = True
        logger.info("EmbeddingModel loaded (feature-hashing, no downloads needed).")

    async def unload(self) -> None:
        self._loaded = False

    async def health_check(self) -> bool:
        return True

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts into fixed-dimension vectors."""
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        await self._ensure_loaded()

        vectors = np.zeros((len(texts), self._dimension), dtype=np.float32)
        for i, text in enumerate(texts):
            vectors[i] = self._hash_embed(text)

        logger.debug("Embedded %d text(s) via feature-hashing.", len(texts))
        return vectors

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string."""
        await self._ensure_loaded()
        return self._hash_embed(query)

    # ── Core hashing algorithm ───────────────────────────────────────────

    def _hash_embed(self, text: str) -> np.ndarray:
        """Convert text to a fixed-dimension vector using feature hashing.

        Algorithm:
        1. Tokenize text into words
        2. For each word, compute multiple hash values
        3. Map hashes to vector indices with random signs
        4. Add bigram features for phrase-level semantics
        5. Apply IDF-like weighting (rare words get higher weight)
        6. L2 normalise the result
        """
        vec = np.zeros(self._dimension, dtype=np.float32)
        tokens = _tokenize(text)

        if not tokens:
            return vec

        # ── Unigram features ─────────────────────────────────────────
        token_counts: dict[str, int] = {}
        for tok in tokens:
            token_counts[tok] = token_counts.get(tok, 0) + 1

        for tok, count in token_counts.items():
            # TF component: sub-linear (log) to dampen frequent terms
            tf = 1.0 + np.log(count) if count > 1 else 1.0

            # Down-weight stop words
            weight = tf * (self._STOP_WEIGHT if tok in _STOP_WORDS else 1.0)

            # Longer words are often more informative
            if len(tok) > 6:
                weight *= 1.2

            for seed in range(self._NUM_HASHES):
                h = hashlib.sha256(f"{seed}:{tok}".encode()).digest()
                idx = int.from_bytes(h[:4], "little") % self._dimension
                sign = 1.0 if h[4] & 1 else -1.0
                vec[idx] += sign * weight

        # ── Bigram features (capture word order / phrases) ───────────
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i + 1]}"
            weight = self._BIGRAM_WEIGHT

            # Down-weight if both are stop words
            if tokens[i] in _STOP_WORDS and tokens[i + 1] in _STOP_WORDS:
                weight *= self._STOP_WEIGHT

            for seed in range(2):  # Fewer hashes for bigrams
                h = hashlib.sha256(f"bi{seed}:{bigram}".encode()).digest()
                idx = int.from_bytes(h[:4], "little") % self._dimension
                sign = 1.0 if h[4] & 1 else -1.0
                vec[idx] += sign * weight

        # ── L2 normalise ─────────────────────────────────────────────
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

        return vec

    # ── Internals ────────────────────────────────────────────────────────

    async def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            await self.load()
