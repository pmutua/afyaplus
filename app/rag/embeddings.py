"""Embedding configuration for the AfyaPlus RAG Agent System.

build_embedding_model() selects an embedding model for the current
environment:

- CI: DeterministicHashEmbedding - no network call, so automated test runs
  stay fast and reproducible. Detected via the ambient CI env var most CI
  providers set automatically (e.g. GitHub Actions sets CI=true).
- Otherwise, EMBEDDING_PROVIDER picks between two local backends (default
  "ollama_local"):
  - "ollama_local": Ollama's OLLAMA_EMBEDDING_MODEL (default
    "embeddinggemma"; "all-minilm" is a supported alternative), reachable
    via OLLAMA_EMBEDDING_BASE_URL. Raises a clear error if Ollama isn't
    reachable or the model isn't pulled, rather than silently substituting
    something else. Requires a running Ollama daemon somewhere reachable -
    fine for local dev, but means a deployed instance either bundles Ollama
    or talks to a separate Ollama service over the network.
  - "fastembed_local": an in-process embedding via the fastembed library
    (ONNX Runtime, no PyTorch, no daemon, no network call at request time),
    default model FASTEMBED_MODEL="BAAI/bge-small-en-v1.5" (67MB, 384-dim).
    Recommended for deployments (e.g. Railway) where running or reaching a
    separate Ollama instance just for embeddings isn't worth the extra
    service - see issue #31.

Embeddings are configured independently from the chat model
(app/config.py): EMBEDDING_PROVIDER, OLLAMA_EMBEDDING_BASE_URL, and
OLLAMA_EMBEDDING_MODEL are separate variables from MODEL_PROVIDER and the
chat OLLAMA_LOCAL_*/OLLAMA_CLOUD_* settings, so switching the chat model to
Ollama Cloud never changes where document embeddings run - both local
backends keep embeddings on-machine, never sent to a third-party API.

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
from typing import Any

import httpx
from dotenv import load_dotenv
from llama_index.core.base.embeddings.base import BaseEmbedding
from pydantic import PrivateAttr

load_dotenv()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DEFAULT_DIMENSIONS = 256
_OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma")
_FASTEMBED_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
_VALID_EMBEDDING_PROVIDERS = ("ollama_local", "fastembed_local")


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


class FastEmbedLocalEmbedding(BaseEmbedding):
    """In-process embedding via fastembed (ONNX Runtime) - no daemon, no network call.

    llama-index-embeddings-fastembed (the obvious integration package) pins
    fastembed<0.2.0, unresolvable against a current fastembed install - this
    is a small hand-rolled wrapper instead, the same pattern as
    DeterministicHashEmbedding above.

    Loading the ONNX model (first construction only - downloads on first
    use, then reads from the local cache) takes real time; each _embed()
    call afterward is fast (single-digit milliseconds for short text).
    Callers on a hot path must construct this once and reuse it - see
    app/rag/retrieval.py's cached default retriever.
    """

    fastembed_model_name: str = _FASTEMBED_MODEL
    _client: Any = PrivateAttr(default=None)

    def __init__(self, model_name: str = _FASTEMBED_MODEL, **kwargs: object) -> None:
        super().__init__(
            model_name=f"fastembed-{model_name}",
            fastembed_model_name=model_name,
            **kwargs,
        )
        from fastembed import TextEmbedding

        self._client = TextEmbedding(model_name=model_name)

    @classmethod
    def class_name(cls) -> str:
        return "FastEmbedLocalEmbedding"

    def _embed(self, text: str) -> list[float]:
        (vector,) = self._client.embed([text])
        return vector.tolist()

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
    between the two. Requires a reachable Ollama daemon; see
    _fastembed_embedding() for a daemon-free alternative.
    """

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


def _fastembed_embedding() -> BaseEmbedding:
    """Build the in-process fastembed model - no daemon, no network call at request time."""

    return FastEmbedLocalEmbedding(model_name=_FASTEMBED_MODEL)


def build_embedding_model() -> BaseEmbedding:
    """Select the embedding model for the current environment. See module docstring."""

    if os.getenv("CI"):
        return DeterministicHashEmbedding()

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "ollama_local")
    if embedding_provider not in _VALID_EMBEDDING_PROVIDERS:
        raise RuntimeError(
            f"EMBEDDING_PROVIDER={embedding_provider!r} is not supported. "
            f"Must be one of {_VALID_EMBEDDING_PROVIDERS} - embeddings "
            "intentionally never leave the local boundary regardless of the "
            "chat MODEL_PROVIDER."
        )
    if embedding_provider == "fastembed_local":
        return _fastembed_embedding()
    return _ollama_embedding()
