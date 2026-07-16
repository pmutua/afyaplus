"""Grounded retrieval over the persisted AfyaPlus knowledge index."""

from __future__ import annotations

from pathlib import Path

from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import NodeWithScore

from app.rag.ingestion import build_index


def build_query_engine(
    knowledge_dir: str | Path | None = None,
    storage_dir: str | Path | None = None,
    collection_name: str | None = None,
    similarity_top_k: int = 3,
) -> BaseQueryEngine:
    """Build a query engine that returns retrieved nodes without LLM synthesis."""

    if knowledge_dir is None:
        index = build_index(
            storage_dir=storage_dir,
            collection_name=collection_name,
        )
    else:
        index = build_index(
            knowledge_dir=knowledge_dir,
            storage_dir=storage_dir,
            collection_name=collection_name,
        )
    return index.as_query_engine(
        similarity_top_k=similarity_top_k,
        response_mode="no_text",
    )


def _source_name(source_node: NodeWithScore) -> str:
    metadata = source_node.metadata
    source = metadata.get("file_name") or metadata.get("file_path")
    return Path(str(source)).name if source else "unknown"


def _format_source(source_node: NodeWithScore) -> str:
    text = source_node.text.strip()
    return f"{text} [Source: {_source_name(source_node)}]"


def query_knowledge(
    question: str,
    knowledge_dir: str | Path | None = None,
    storage_dir: str | Path | None = None,
    collection_name: str | None = None,
    similarity_top_k: int = 3,
) -> str:
    """Return grounded source excerpts with inline filename citations."""

    if not question.strip():
        return "A knowledge question is required."
    query_engine = build_query_engine(
        knowledge_dir,
        storage_dir,
        collection_name,
        similarity_top_k,
    )
    response = query_engine.query(question)
    if not response.source_nodes:
        return "No knowledge sources were retrieved."
    return "\n\n".join(_format_source(node) for node in response.source_nodes)
