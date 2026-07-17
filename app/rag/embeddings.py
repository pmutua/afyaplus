"""Ollama embedding configuration for the AfyaPlus RAG Agent System.

build_embedding_model() selects an embedding model for the current
environment:

- CI: DeterministicHashEmbedding - no network call, so automated test runs
  stay fast and reproducible. Detected via the ambient CI env var most CI
  providers set automatically (e.g. GitHub Actions sets CI=true).
- Otherwise: Ollama's OLLAMA_EMBEDDING_MODEL (default "embeddinggemma";
  "all-minilm" is a supported alternative), reachable via
  OLLAMA_EMBEDDING_BASE_URL. The same model backs both local development
  (Ollama on localhost) and production (self-hosted Ollama elsewhere) - only
  OLLAMA_EMBEDDING_BASE_URL differs between them. Raises a clear error if
  Ollama isn't reachable or the model isn't pulled, rather than silently
  substituting something else.

Embeddings are configured independently from the chat model
(app/config.py): EMBEDDING_PROVIDER, OLLAMA_EMBEDDING_BASE_URL, and
OLLAMA_EMBEDDING_MODEL are separate variables from MODEL_PROVIDER and the
chat OLLAMA_LOCAL_*/OLLAMA_CLOUD_* settings, so switching the chat model to
Ollama Cloud never changes where document embeddings run - they stay on
the local Ollama instance by default. Only EMBEDDING_PROVIDER=ollama_local
is currently supported.

DeterministicHashEmbedding is a bag-of-words hashing-trick embedding
(Weinberger et al. feature hashing): no network call, no API key. Unlike
LlamaIndex's MockEmbedding (a single fixed vector returned for every input,
with no relation to text content at all), texts sharing more words land
closer together in vector space here, so retrieval over it is still
meaningful rather than random - important since it's what CI actually
grades against for anything retrieval-shaped.

Ingestion (chunking.py), index build (ingestion.py), and the ChromaDB
vector store config (vector_store.py) land alongside this module in SPEC-2.3.
"""

from __future__ import annotations

import hashlib
import os
import re

import httpx
from dotenv import load_dotenv
from llama_index.core.base.embeddings.base import BaseEmbedding

load_dotenv()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DEFAULT_DIMENSIONS = 256
_OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma")


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


def _ollama_host() -> str:
    """Root host for the native Ollama client.

    Derived from OLLAMA_EMBEDDING_BASE_URL. Accepts either the bare host or
    a URL with an /v1 suffix (the OpenAI-compatible shape used elsewhere) -
    the native ollama client used here wants just the host root.
    """

    base_url = os.getenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434")
    return base_url.removesuffix("/v1")


def _ollama_embedding() -> BaseEmbedding:
    """Build the Ollama-backed embedding model, raising a clear error if unavailable.

    Backs both local development (Ollama on localhost) and production
    (self-hosted Ollama elsewhere) - only OLLAMA_EMBEDDING_BASE_URL differs
    between the two.
    """

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "ollama_local")
    if embedding_provider != "ollama_local":
        raise RuntimeError(
            f"EMBEDDING_PROVIDER={embedding_provider!r} is not supported. "
            "Only 'ollama_local' is currently implemented - embeddings "
            "intentionally stay local regardless of the chat MODEL_PROVIDER."
        )

    host = _ollama_host()
    try:
        response = httpx.get(f"{host}/api/tags", timeout=1.0)
        response.raise_for_status()
        pulled_models = {model["name"] for model in response.json().get("models", [])}
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError(
            f"Ollama isn't reachable at {host}. Start it with `ollama serve`, "
            "or set OLLAMA_EMBEDDING_BASE_URL to point at a running instance."
        ) from error

    is_pulled = any(
        name == _OLLAMA_EMBEDDING_MODEL or name.startswith(f"{_OLLAMA_EMBEDDING_MODEL}:")
        for name in pulled_models
    )
    if not is_pulled:
        raise RuntimeError(
            f"Ollama is reachable but {_OLLAMA_EMBEDDING_MODEL} isn't pulled "
            f"(try: ollama pull {_OLLAMA_EMBEDDING_MODEL})."
        )

    from llama_index.embeddings.ollama import OllamaEmbedding

    return OllamaEmbedding(model_name=_OLLAMA_EMBEDDING_MODEL, base_url=host)


def build_embedding_model() -> BaseEmbedding:
    """Select the embedding model for the current environment. See module docstring."""

    if os.getenv("CI"):
        return DeterministicHashEmbedding()
    return _ollama_embedding()
