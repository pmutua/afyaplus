from pathlib import Path

import pytest

from app.agent.tools.knowledge import search_afyaplus_knowledge
from app.rag.retrieval import query_knowledge


def test_returns_retrieved_text_with_inline_source_citation(
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
        "What is the maternity waiting period?",
        knowledge_dir=knowledge_dir,
        storage_dir=tmp_path / "chroma",
        collection_name="citation_test",
        similarity_top_k=1,
    )

    assert "six-month waiting period" in result
    assert "[Source: insurance_policy.txt]" in result


def test_langchain_tool_is_scoped_and_returns_cited_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("CHROMA_STORAGE_DIR", str(tmp_path / "tool_chroma"))
    monkeypatch.setenv("CHROMA_COLLECTION_NAME", "tool_test")

    result = search_afyaplus_knowledge.invoke(
        {"question": "What is the maternity coverage waiting period?"}
    )

    assert search_afyaplus_knowledge.name == "search_afyaplus_knowledge"
    description = " ".join(search_afyaplus_knowledge.description.split())
    assert "Do not use it for diagnosis" in description
    assert "[Source: insurance_verification_policy.txt]" in result
