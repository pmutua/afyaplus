from pathlib import Path

import pytest

from app.agent.tools.knowledge import search_afyaplus_knowledge
from app.rag import retrieval
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


def test_default_retriever_is_built_once_per_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """query_knowledge() with default args reuses one cached retriever.

    Reflects the real agent's call pattern (search_afyaplus_knowledge always
    calls query_knowledge(question) with no explicit paths) - every question
    in a session must not repay the cost of reopening ChromaDB and rebuilding
    the embedding model. Calls with explicit paths (the other tests in this
    file) always bypass this cache and build fresh instead.
    """

    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("CHROMA_STORAGE_DIR", str(tmp_path / "cache_test"))
    monkeypatch.setenv("CHROMA_COLLECTION_NAME", "cache_test")

    first = retrieval._cached_default_retriever(3)
    second = retrieval._cached_default_retriever(3)

    assert first is second
