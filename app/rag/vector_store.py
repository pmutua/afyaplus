"""ChromaDB vector store configuration for the AfyaPlus RAG Agent System.

Persists to top-level storage/chroma/ via Chroma's PersistentClient, so the
index survives across process restarts (SPEC-2.4 adds the "reload instead
of re-ingest" check on top of this).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

_DEFAULT_STORAGE_DIR = "storage/chroma"
_DEFAULT_COLLECTION_NAME = "afyaplus_knowledge_base"


@dataclass(frozen=True)
class VectorStoreHandle:
    """A persistent vector store and whether it already contains nodes."""

    vector_store: ChromaVectorStore
    has_nodes: bool


def open_vector_store(
    storage_dir: str | Path | None = None,
    collection_name: str | None = None,
) -> VectorStoreHandle:
    """Open the persistent collection and report whether it has indexed nodes."""

    resolved_dir = storage_dir or os.getenv("CHROMA_STORAGE_DIR", _DEFAULT_STORAGE_DIR)
    resolved_name = collection_name or os.getenv(
        "CHROMA_COLLECTION_NAME", _DEFAULT_COLLECTION_NAME
    )
    client = chromadb.PersistentClient(path=str(resolved_dir))
    collection = client.get_or_create_collection(resolved_name, embedding_function=None)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreHandle(vector_store=vector_store, has_nodes=collection.count() > 0)


def build_vector_store(
    storage_dir: str | Path | None = None,
    collection_name: str | None = None,
) -> ChromaVectorStore:
    """Build the ChromaDB-backed vector store, persisted to CHROMA_STORAGE_DIR.

    embedding_function=None keeps Chroma from ever computing its own
    embeddings - LlamaIndex always supplies precomputed vectors from
    app.rag.embeddings.build_embedding_model(), so Chroma's default
    embedder (which would need its own model download) is never invoked.
    """

    return open_vector_store(storage_dir, collection_name).vector_store
