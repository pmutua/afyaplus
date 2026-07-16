"""ChromaDB vector store configuration for the AfyaPlus RAG Agent System.

Persists to top-level storage/chroma/ via Chroma's PersistentClient, so the
index survives across process restarts (SPEC-2.4 adds the "reload instead
of re-ingest" check on top of this).
"""

from __future__ import annotations

import os

import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

_STORAGE_DIR = os.getenv("CHROMA_STORAGE_DIR", "storage/chroma")
_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "afyaplus_knowledge_base")


def build_vector_store() -> ChromaVectorStore:
    """Build the ChromaDB-backed vector store, persisted to CHROMA_STORAGE_DIR.

    embedding_function=None keeps Chroma from ever computing its own
    embeddings - LlamaIndex always supplies precomputed vectors from
    app.rag.embeddings.build_embedding_model(), so Chroma's default
    embedder (which would need its own model download) is never invoked.
    """

    client = chromadb.PersistentClient(path=_STORAGE_DIR)
    collection = client.get_or_create_collection(_COLLECTION_NAME, embedding_function=None)
    return ChromaVectorStore(chroma_collection=collection)
