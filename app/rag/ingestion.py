"""Build the VectorStoreIndex over the AfyaPlus knowledge base (top-level knowledge/)."""

from __future__ import annotations

from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex

from app.rag.chunking import build_node_parser
from app.rag.embeddings import build_embedding_model
from app.rag.vector_store import open_vector_store

_KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


def build_index(
    knowledge_dir: str | Path = _KNOWLEDGE_DIR,
    storage_dir: str | Path | None = None,
    collection_name: str | None = None,
) -> VectorStoreIndex:
    """Build a new index or reload nodes already persisted in ChromaDB."""

    handle = open_vector_store(storage_dir, collection_name)
    embedding_model = build_embedding_model()
    if handle.has_nodes:
        return VectorStoreIndex.from_vector_store(
            handle.vector_store,
            embed_model=embedding_model,
        )

    documents = SimpleDirectoryReader(str(knowledge_dir)).load_data()
    storage_context = StorageContext.from_defaults(vector_store=handle.vector_store)
    return VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embedding_model,
        transformations=[build_node_parser()],
    )
