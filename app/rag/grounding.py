"""Grounding rules shared by retrieval and the future agent prompt."""

from __future__ import annotations

import re
from collections.abc import Sequence

from llama_index.core.schema import NodeWithScore

NOT_FOUND_RESPONSE = "Information not found."
GROUNDING_SYSTEM_PROMPT = f"""
For policy and routing questions, answer only from the retrieved AfyaPlus
knowledge sources. Keep source citations with supported claims. If the sources
do not contain enough information to answer the question, respond exactly:
{NOT_FOUND_RESPONSE}
""".strip()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "do",
    "does",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def _normalize(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[: -len(suffix)]
    return token


def _keywords(text: str) -> set[str]:
    return {
        _normalize(token)
        for token in _TOKEN_PATTERN.findall(text.lower())
        if token not in _STOP_WORDS and len(token) > 2
    }


def select_grounded_sources(
    question: str,
    source_nodes: Sequence[NodeWithScore],
) -> list[NodeWithScore]:
    """Keep sources containing substantive terms from the user's question."""

    question_keywords = _keywords(question)
    if not question_keywords:
        return []
    return [
        source_node
        for source_node in source_nodes
        if question_keywords & _keywords(source_node.text)
    ]
