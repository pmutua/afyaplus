"""Grounded retrieval through Qdrant Cloud Inference."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from qdrant_client import QdrantClient

from app.rag.embeddings import InferenceConfig, inference_document
from app.rag.grounding import NOT_FOUND_RESPONSE, select_grounded_sources
from app.rag.ingestion import ingest_knowledge
from app.rag.vector_store import VectorStoreHandle, open_vector_store


class QdrantRetriever(BaseRetriever):
    """Adapt Qdrant results to the LlamaIndex retriever contract."""

    def __init__(self, handle: VectorStoreHandle, similarity_top_k: int) -> None:
        super().__init__()
        self._client = handle.client
        self._collection_name = handle.settings.collection_name
        self._inference = handle.settings.inference
        self._similarity_top_k = similarity_top_k

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=inference_document(query_bundle.query_str, self._inference),
            with_payload=True,
            limit=self._similarity_top_k,
        )
        return [_to_node(point) for point in response.points]


def _to_node(point: Any) -> NodeWithScore:
    payload = point.payload or {}
    metadata = payload.get("metadata") or {}
    node = TextNode(text=str(payload.get("text", "")), metadata=dict(metadata))
    return NodeWithScore(node=node, score=float(point.score))


def build_retriever(
    knowledge_dir: str | Path | None = None,
    collection_name: str | None = None,
    similarity_top_k: int = 3,
    client: QdrantClient | None = None,
) -> BaseRetriever:
    """Ensure knowledge is indexed, then build a Qdrant-backed retriever."""

    ingestion_kwargs: dict[str, object] = {
        "collection_name": collection_name,
        "client": client,
    }
    if knowledge_dir is not None:
        ingestion_kwargs["knowledge_dir"] = knowledge_dir
    ingest_knowledge(**ingestion_kwargs)
    handle = open_vector_store(collection_name, client)
    return QdrantRetriever(handle, similarity_top_k)


@lru_cache(maxsize=1)
def _cached_default_retriever(similarity_top_k: int) -> BaseRetriever:
    """Reuse the production Qdrant client and retriever for the process lifetime."""

    return build_retriever(similarity_top_k=similarity_top_k)


def _source_name(source_node: NodeWithScore) -> str:
    source = source_node.metadata.get("file_name") or source_node.metadata.get(
        "file_path"
    )
    return Path(str(source)).name if source else "unknown"


def _format_source(source_node: NodeWithScore) -> str:
    return f"{source_node.text.strip()} [Source: {_source_name(source_node)}]"


def query_knowledge(
    question: str,
    knowledge_dir: str | Path | None = None,
    collection_name: str | None = None,
    similarity_top_k: int = 3,
    client: QdrantClient | None = None,
) -> str:
    """Return grounded source excerpts with inline filename citations."""

    if not question.strip():
        return "A knowledge question is required."
    if knowledge_dir is None and collection_name is None and client is None:
        retriever = _cached_default_retriever(similarity_top_k)
    else:
        retriever = build_retriever(
            knowledge_dir, collection_name, similarity_top_k, client
        )
    grounded = select_grounded_sources(question, retriever.retrieve(question))
    if not grounded:
        return NOT_FOUND_RESPONSE
    return "\n\n".join(_format_source(node) for node in grounded)
