"""Grounded LlamaIndex knowledge pipeline for the AfyaPlus RAG Agent System.

DeterministicHashEmbedding is the default embedding model: a bag-of-words
hashing-trick embedding (Weinberger et al. feature hashing) that requires no
network call and no API key, so it costs nothing to run in local dev, CI, or
grading. Unlike LlamaIndex's MockEmbedding (a single fixed vector returned
for every input, with no relation to text content at all), texts sharing
more words land closer together in vector space here, so retrieval over it
is still meaningful rather than random.

build_embedding_model() opts into real OpenAI embeddings instead, but only
when a genuine (non-placeholder) OPENAI_API_KEY is configured.

Ingestion (chunking + index build) lands in SPEC-2.3.
"""

from __future__ import annotations

import hashlib
import os
import re

from dotenv import load_dotenv
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

load_dotenv()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DEFAULT_DIMENSIONS = 256


def valid_env_value(name: str) -> str | None:
    """Return an environment value only when it is not a placeholder."""

    value = os.getenv(name)
    if not value or "your-" in value.lower():
        return None
    return value


class DeterministicHashEmbedding(BaseEmbedding):
    """Deterministic bag-of-words embedding using the signed hashing trick.

    Same text always produces the same vector: no randomness, no network
    call. Each token is hashed to a dimension index and a +1/-1 sign, so
    cosine similarity between two vectors reflects real word overlap
    between the two texts.
    """

    dimensions: int = _DEFAULT_DIMENSIONS

    def __init__(self, dimensions: int = _DEFAULT_DIMENSIONS, **kwargs: object) -> None:
        super().__init__(
            model_name="local-deterministic-hash",
            dimensions=dimensions,
            **kwargs,
        )

    @classmethod
    def class_name(cls) -> str:
        return "DeterministicHashEmbedding"

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = sum(component * component for component in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [component / norm for component in vector]

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)


def build_embedding_model() -> BaseEmbedding:
    """Return OpenAI embeddings when a genuine API key is configured.

    Falls back to DeterministicHashEmbedding otherwise. Embeddings are
    requested directly from OpenAI rather than OpenRouter, since embedding
    endpoint support varies by OpenRouter provider; this is independent of
    whichever cloud chat provider the triage engine or agent core uses.
    """

    api_key = valid_env_value("OPENAI_API_KEY")
    if api_key:
        return OpenAIEmbedding(
            api_key=api_key,
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
    return DeterministicHashEmbedding()
