"""Grounded LlamaIndex knowledge pipeline for the AfyaPlus RAG Agent System.

build_embedding_model() selects an embedding tier for the current
environment:

- CI always wins first: DeterministicHashEmbedding whenever the ambient CI
  env var is set (GitHub Actions/GitLab CI/etc. set this automatically) -
  even if EMBEDDING_PROVIDER or a cloud key is also present, so automated
  test runs never make a real network call.
- If EMBEDDING_PROVIDER is set (openrouter/openai/ollama/huggingface/
  deterministic), that exact tier is used, raising a clear error if its
  requirements aren't met (e.g. EMBEDDING_PROVIDER=ollama but Ollama isn't
  reachable) rather than silently substituting a different tier.
- Otherwise, auto-detect in this order: OpenRouter or direct OpenAI real
  embeddings if a genuine cloud key is configured (production) -> Ollama's
  OLLAMA_EMBEDDING_MODEL if Ollama is reachable and has it pulled (local
  dev, preferred) -> BAAI/bge-small-en-v1.5 via
  llama-index-embeddings-huggingface, a requirements-dev.txt-only
  dependency, if installed (local dev, fallback) -> DeterministicHashEmbedding
  as a last resort so the pipeline still runs on a fresh machine with
  nothing configured yet.

DeterministicHashEmbedding itself is a bag-of-words hashing-trick embedding
(Weinberger et al. feature hashing): no network call, no API key. Unlike
LlamaIndex's MockEmbedding (a single fixed vector returned for every input,
with no relation to text content at all), texts sharing more words land
closer together in vector space here, so retrieval over it is still
meaningful rather than random.

Ingestion (chunking + index build) lands in SPEC-2.3.
"""

from __future__ import annotations

import hashlib
import os
import re

import httpx
from dotenv import load_dotenv
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from openai import OpenAI

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


class OpenAICompatibleEmbedding(BaseEmbedding):
    """Embedding backed by any OpenAI-compatible /embeddings endpoint.

    Uses the raw openai client directly - the same one triage/engine.py
    uses for chat - instead of LlamaIndex's OpenAIEmbedding wrapper, which
    validates `model` against a closed enum of exactly seven literal
    OpenAI model names and raises on anything else, including
    OpenRouter-style provider-prefixed names like
    "openai/text-embedding-3-small" or arbitrary third-party model IDs.
    """

    api_key: str = Field(description="API key for the OpenAI-compatible endpoint.")
    api_base: str = Field(description="Base URL for the OpenAI-compatible endpoint.")

    _client: OpenAI = PrivateAttr()

    def __init__(self, model: str, api_key: str, api_base: str, **kwargs: object) -> None:
        super().__init__(model_name=model, api_key=api_key, api_base=api_base, **kwargs)
        self._client = OpenAI(api_key=api_key, base_url=api_base)

    @classmethod
    def class_name(cls) -> str:
        return "OpenAICompatibleEmbedding"

    def _embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self.model_name, input=text)
        return response.data[0].embedding

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)


_OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma")


def _ollama_host() -> str:
    """Root host for the native Ollama client.

    Derived from OLLAMA_BASE_URL, which includes a /v1 suffix for the
    OpenAI-compatible client the triage engine uses elsewhere; the native
    ollama client used here wants just the host root.
    """

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    return base_url.removesuffix("/v1")


def _ollama_embedding_if_reachable() -> BaseEmbedding | None:
    """Return an Ollama-backed embedding model, or None if unavailable.

    None is returned (rather than raising) whenever Ollama isn't running or
    OLLAMA_EMBEDDING_MODEL hasn't been pulled, so the caller can fall
    through to the next tier instead of crashing.
    """

    host = _ollama_host()
    try:
        response = httpx.get(f"{host}/api/tags", timeout=1.0)
        response.raise_for_status()
        pulled_models = {model["name"] for model in response.json().get("models", [])}
    except (httpx.HTTPError, ValueError):
        return None

    is_pulled = any(
        name == _OLLAMA_EMBEDDING_MODEL or name.startswith(f"{_OLLAMA_EMBEDDING_MODEL}:")
        for name in pulled_models
    )
    if not is_pulled:
        return None

    try:
        from llama_index.embeddings.ollama import OllamaEmbedding
    except ImportError:
        return None
    return OllamaEmbedding(model_name=_OLLAMA_EMBEDDING_MODEL, base_url=host)


def _huggingface_embedding() -> BaseEmbedding | None:
    """Return the BAAI/bge-small-en-v1.5 local embedding model, or None.

    Requires the requirements-dev.txt-only dependencies
    (llama-index-embeddings-huggingface, sentence-transformers). Returns
    None rather than raising when they aren't installed, so the pipeline
    still runs on the deterministic fallback instead of crashing on a
    missing optional dependency.
    """

    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    except ImportError:
        return None
    return HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")


def _openrouter_embedding() -> BaseEmbedding:
    """Build OpenRouter embeddings, raising if OPENROUTER_API_KEY isn't genuinely set."""

    api_key = valid_env_value("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "EMBEDDING_PROVIDER=openrouter but OPENROUTER_API_KEY is missing or a placeholder."
        )
    return OpenAICompatibleEmbedding(
        api_key=api_key,
        api_base=os.getenv("MODEL_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
    )


def _openai_embedding() -> BaseEmbedding:
    """Build direct OpenAI embeddings, raising if OPENAI_API_KEY isn't genuinely set."""

    api_key = valid_env_value("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is missing or a placeholder."
        )
    return OpenAICompatibleEmbedding(
        api_key=api_key,
        api_base=os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )


_EXPLICIT_PROVIDERS = {"openrouter", "openai", "ollama", "huggingface", "deterministic"}


def _build_explicit_provider(provider: str) -> BaseEmbedding:
    """Build exactly the tier named by EMBEDDING_PROVIDER, raising if it can't be satisfied."""

    if provider == "openrouter":
        return _openrouter_embedding()
    if provider == "openai":
        return _openai_embedding()
    if provider == "ollama":
        ollama_embedding = _ollama_embedding_if_reachable()
        if ollama_embedding is None:
            raise RuntimeError(
                f"EMBEDDING_PROVIDER=ollama but Ollama isn't reachable or "
                f"{_OLLAMA_EMBEDDING_MODEL} isn't pulled (try: ollama pull {_OLLAMA_EMBEDDING_MODEL})."
            )
        return ollama_embedding
    if provider == "huggingface":
        huggingface_embedding = _huggingface_embedding()
        if huggingface_embedding is None:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=huggingface but its dependencies aren't installed - "
                "pip install -r requirements-dev.txt"
            )
        return huggingface_embedding
    if provider == "deterministic":
        return DeterministicHashEmbedding()

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER={provider!r}; expected one of {sorted(_EXPLICIT_PROVIDERS)}."
    )


def _auto_detect_embedding_model() -> BaseEmbedding:
    """Auto-detect a tier when EMBEDDING_PROVIDER isn't set. See module docstring for order."""

    if valid_env_value("OPENROUTER_API_KEY"):
        return _openrouter_embedding()
    if valid_env_value("OPENAI_API_KEY"):
        return _openai_embedding()

    ollama_embedding = _ollama_embedding_if_reachable()
    if ollama_embedding is not None:
        return ollama_embedding

    huggingface_embedding = _huggingface_embedding()
    if huggingface_embedding is not None:
        return huggingface_embedding

    print(
        "[WARN] No cloud key, Ollama, or Hugging Face embedding available; "
        "falling back to DeterministicHashEmbedding."
    )
    return DeterministicHashEmbedding()


def build_embedding_model() -> BaseEmbedding:
    """Select the embedding tier for the current environment. See module docstring."""

    if os.getenv("CI"):
        return DeterministicHashEmbedding()

    provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    if provider:
        return _build_explicit_provider(provider)

    return _auto_detect_embedding_model()
