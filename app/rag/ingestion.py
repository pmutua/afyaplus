"""Build the VectorStoreIndex over the AfyaPlus knowledge base (top-level knowledge/)."""

from __future__ import annotations

from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex

from app.rag.chunking import build_node_parser
from app.rag.embeddings import build_embedding_model
from app.rag.vector_store import build_vector_store

_KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


def build_index() -> VectorStoreIndex:
    """Ingest documents from knowledge/ into the ChromaDB-backed vector index."""

    documents = SimpleDirectoryReader(str(_KNOWLEDGE_DIR)).load_data()
    storage_context = StorageContext.from_defaults(vector_store=build_vector_store())
    return VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=build_embedding_model(),
        transformations=[build_node_parser()],
    )
