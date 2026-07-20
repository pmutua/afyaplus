"""Sentence-aware LlamaIndex chunking for the AfyaPlus knowledge base."""

from __future__ import annotations

from llama_index.core.node_parser import SentenceSplitter

_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64


def build_node_parser() -> SentenceSplitter:
    """Build a deterministic parser that requires no local embedding model."""

    return SentenceSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )
