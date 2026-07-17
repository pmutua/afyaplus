"""Qdrant Cloud vector-store configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

from app.rag.embeddings import InferenceConfig, load_inference_config

_DEFAULT_COLLECTION = "afyaplus_knowledge_base"
_DEFAULT_TIMEOUT_SECONDS = 30.0

load_dotenv()


@dataclass(frozen=True)
class QdrantSettings:
    """Validated connection settings for Qdrant Cloud."""

    url: str
    api_key: str
    collection_name: str
    timeout_seconds: float
    inference: InferenceConfig


@dataclass(frozen=True)
class VectorStoreHandle:
    """A Qdrant client, collection, and current persistence state."""

    client: QdrantClient
    settings: QdrantSettings
    has_nodes: bool


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(f"{name} is required for Qdrant Cloud.")
    return value


def _validated_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("QDRANT_URL must be a valid HTTPS URL.")
    return value.rstrip("/")


def load_qdrant_settings(
    collection_name: str | None = None,
) -> QdrantSettings:
    """Load Qdrant secrets and non-secret inference settings."""

    raw_timeout = os.getenv("QDRANT_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS))
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError as error:
        raise RuntimeError("QDRANT_TIMEOUT_SECONDS must be numeric.") from error
    if timeout_seconds <= 0:
        raise RuntimeError("QDRANT_TIMEOUT_SECONDS must be positive.")
    resolved_collection = collection_name or os.getenv(
        "QDRANT_COLLECTION_NAME", _DEFAULT_COLLECTION
    )
    if not resolved_collection.strip():
        raise RuntimeError("QDRANT_COLLECTION_NAME must not be empty.")
    return QdrantSettings(
        url=_validated_url(_required_env("QDRANT_URL")),
        api_key=_required_env("QDRANT_API_KEY"),
        collection_name=resolved_collection,
        timeout_seconds=timeout_seconds,
        inference=load_inference_config(),
    )


def build_qdrant_client(settings: QdrantSettings) -> QdrantClient:
    """Build the official client with managed inference enabled."""

    return QdrantClient(
        url=settings.url,
        api_key=settings.api_key,
        cloud_inference=True,
        timeout=settings.timeout_seconds,
    )


def _ensure_collection(client: QdrantClient, settings: QdrantSettings) -> None:
    if client.collection_exists(settings.collection_name):
        return
    client.create_collection(
        collection_name=settings.collection_name,
        vectors_config=models.VectorParams(
            size=settings.inference.dimensions,
            distance=models.Distance.COSINE,
        ),
        metadata={"embedding_model": settings.inference.model},
    )


def open_vector_store(
    collection_name: str | None = None,
    client: QdrantClient | None = None,
) -> VectorStoreHandle:
    """Open or create the configured collection and report whether it has data."""

    settings = load_qdrant_settings(collection_name)
    resolved_client = client or build_qdrant_client(settings)
    _ensure_collection(resolved_client, settings)
    count = resolved_client.count(settings.collection_name, exact=True).count
    return VectorStoreHandle(resolved_client, settings, has_nodes=count > 0)
