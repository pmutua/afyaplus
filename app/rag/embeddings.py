"""Qdrant Cloud Inference model configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from qdrant_client import models

_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_DIMENSIONS = 384


@dataclass(frozen=True)
class InferenceConfig:
    """Embedding model details shared by ingestion and retrieval."""

    model: str
    dimensions: int


def load_inference_config() -> InferenceConfig:
    """Load and validate the managed embedding model configuration."""

    model = os.getenv("QDRANT_EMBEDDING_MODEL", _DEFAULT_MODEL).strip()
    raw_dimensions = os.getenv(
        "QDRANT_EMBEDDING_DIMENSIONS", str(_DEFAULT_DIMENSIONS)
    )
    try:
        dimensions = int(raw_dimensions)
    except ValueError as error:
        raise RuntimeError("QDRANT_EMBEDDING_DIMENSIONS must be an integer.") from error
    if not model:
        raise RuntimeError("QDRANT_EMBEDDING_MODEL must not be empty.")
    if dimensions <= 0:
        raise RuntimeError("QDRANT_EMBEDDING_DIMENSIONS must be positive.")
    return InferenceConfig(model=model, dimensions=dimensions)


def inference_document(text: str, config: InferenceConfig) -> models.Document:
    """Build a Qdrant inference object without embedding text locally."""

    return models.Document(text=text, model=config.model)
