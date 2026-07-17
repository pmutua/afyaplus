"""Ingest the AfyaPlus knowledge base through Qdrant Cloud Inference."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import BaseNode
from qdrant_client import QdrantClient, models

from app.rag.chunking import build_node_parser
from app.rag.embeddings import InferenceConfig, inference_document
from app.rag.vector_store import open_vector_store

_KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of an idempotent knowledge ingestion attempt."""

    indexed_nodes: int
    reused_existing: bool


def _point_id(node: BaseNode) -> str:
    source = str(node.metadata.get("file_name", "unknown"))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}\n{node.text}"))


def _point(node: BaseNode, inference: InferenceConfig) -> models.PointStruct:
    metadata = {"file_name": str(node.metadata.get("file_name", "unknown"))}
    payload = {"text": node.text, "metadata": metadata}
    return models.PointStruct(
        id=_point_id(node),
        vector=inference_document(node.text, inference),
        payload=payload,
    )


def _load_nodes(knowledge_dir: str | Path) -> list[BaseNode]:
    documents = SimpleDirectoryReader(str(knowledge_dir)).load_data()
    return build_node_parser().get_nodes_from_documents(documents)


def ingest_knowledge(
    knowledge_dir: str | Path = _KNOWLEDGE_DIR,
    collection_name: str | None = None,
    client: QdrantClient | None = None,
) -> IngestionResult:
    """Create the collection once and reuse it on later process starts."""

    handle = open_vector_store(collection_name, client)
    if handle.has_nodes:
        return IngestionResult(indexed_nodes=0, reused_existing=True)
    nodes = _load_nodes(knowledge_dir)
    points = [_point(node, handle.settings.inference) for node in nodes]
    handle.client.upload_points(
        collection_name=handle.settings.collection_name,
        points=points,
        batch_size=8,
        max_retries=3,
        wait=True,
    )
    return IngestionResult(indexed_nodes=len(points), reused_existing=False)
