from pathlib import Path

import pytest

from app.rag.grounding import GROUNDING_SYSTEM_PROMPT, NOT_FOUND_RESPONSE
from app.rag.retrieval import query_knowledge


def test_returns_exact_not_found_for_ungrounded_question(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI", "true")
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "insurance_policy.txt").write_text(
        "AfyaPlus maternity cover has a six-month waiting period.",
        encoding="utf-8",
    )

    result = query_knowledge(
        "How do I bake sourdough bread?",
        knowledge_dir=knowledge_dir,
        storage_dir=tmp_path / "chroma",
        collection_name="grounding_test",
        similarity_top_k=1,
    )

    assert result == NOT_FOUND_RESPONSE
    assert NOT_FOUND_RESPONSE in GROUNDING_SYSTEM_PROMPT
