"""Grounded retrieval over the persisted AfyaPlus knowledge index."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import NodeWithScore

from app.rag.grounding import NOT_FOUND_RESPONSE, select_grounded_sources
from app.rag.ingestion import build_index


def build_retriever(
    knowledge_dir: str | Path | None = None,
    storage_dir: str | Path | None = None,
    collection_name: str | None = None,
    similarity_top_k: int = 3,
) -> BaseRetriever:
    """Build a retriever over the persisted index - no LLM synthesis involved.

    Grounding only ever needs the retrieved nodes (see query_knowledge()), so
    this returns a plain retriever rather than a full query engine: LlamaIndex's
    query-engine/response-synthesizer path resolves a default LLM as a side
    effect even for response_mode="no_text" (a library quirk - the NO_TEXT
    branch of get_response_synthesizer() drops the llm kwarg it's given), which
    would otherwise require a real or mocked LLM for no functional benefit here.
    """

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
    return index.as_retriever(similarity_top_k=similarity_top_k)


@lru_cache(maxsize=1)
def _cached_default_retriever(similarity_top_k: int) -> BaseRetriever:
    """Process-lifetime cache for the production (env-resolved) retriever.

    Building a retriever opens ChromaDB's PersistentClient, constructs the
    embedding model, and reloads the persisted index - real work that must
    happen once per process, not on every knowledge-tool call (the agent
    calls query_knowledge() fresh on every question). Only used for the
    default knowledge_dir/storage_dir/collection_name (env-resolved) - see
    query_knowledge() below. Callers passing explicit paths (tests using a
    tmp_path fixture) always bypass this and build fresh.
    """

    return build_retriever(similarity_top_k=similarity_top_k)


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
    if knowledge_dir is None and storage_dir is None and collection_name is None:
        retriever = _cached_default_retriever(similarity_top_k)
    else:
        retriever = build_retriever(
            knowledge_dir,
            storage_dir,
            collection_name,
            similarity_top_k,
        )
    retrieved_nodes = retriever.retrieve(question)
    grounded_sources = select_grounded_sources(question, retrieved_nodes)
    if not grounded_sources:
        return NOT_FOUND_RESPONSE
    return "\n\n".join(_format_source(node) for node in grounded_sources)
