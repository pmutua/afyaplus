from pathlib import Path

import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from app.rag.grounding import GROUNDING_SYSTEM_PROMPT, NOT_FOUND_RESPONSE, select_grounded_sources
from app.rag.retrieval import query_knowledge
from tests.qdrant_fakes import FakeQdrantClient


def test_returns_exact_not_found_for_ungrounded_question(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_URL", "https://test.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "test-api-key")
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "insurance_policy.txt").write_text(
        "AfyaPlus maternity cover has a six-month waiting period.",
        encoding="utf-8",
    )

    result = query_knowledge(
        "How do I bake sourdough bread?",
        knowledge_dir=knowledge_dir,
        collection_name="grounding_test",
        similarity_top_k=1,
        client=FakeQdrantClient(),
    )

    assert result == NOT_FOUND_RESPONSE
    assert NOT_FOUND_RESPONSE in GROUNDING_SYSTEM_PROMPT


def test_grounded_sources_are_capped_even_when_more_match() -> None:
    """A generic keyword shared with many chunks of a large document must not
    flood the model with every matching chunk concatenated together - that
    produced an unmanageable wall of text that overwhelmed the chat model's
    synthesis step for real production questions (e.g. "How does AfyaPlus
    coordinate benefits with SHA or SHIF?")."""

    nodes = [
        NodeWithScore(
            node=TextNode(text=f"AfyaPlus benefit coordination detail {i}."),
            score=1.0 - i * 0.01,
        )
        for i in range(6)
    ]

    grounded = select_grounded_sources("How does AfyaPlus coordinate benefits?", nodes)

    assert len(grounded) == 2
    assert grounded == nodes[:2]
