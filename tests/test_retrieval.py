from pathlib import Path

import pytest

from app.agent.tools.knowledge import search_afyaplus_knowledge
from app.rag import retrieval, vector_store
from app.rag.retrieval import query_knowledge
from tests.qdrant_fakes import FakeQdrantClient


@pytest.fixture
def qdrant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "https://test.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "test-api-key")


def test_returns_retrieved_text_with_inline_source_citation(
    tmp_path: Path,
    qdrant_env: None,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "insurance_policy.txt").write_text(
        "AfyaPlus maternity cover has a six-month waiting period.",
        encoding="utf-8",
    )

    result = query_knowledge(
        "What is the maternity waiting period?",
        knowledge_dir=knowledge_dir,
        collection_name="citation_test",
        similarity_top_k=1,
        client=FakeQdrantClient(),
    )

    assert "six-month waiting period" in result
    assert "[Source: insurance_policy.txt]" in result


def test_langchain_tool_returns_cited_policy(
    qdrant_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeQdrantClient()
    monkeypatch.setattr(vector_store, "build_qdrant_client", lambda settings: client)

    result = search_afyaplus_knowledge.invoke(
        {"question": "What is the maternity coverage waiting period?"}
    )

    assert search_afyaplus_knowledge.name == "search_afyaplus_knowledge"
    description = " ".join(search_afyaplus_knowledge.description.split())
    assert "Do not use it for diagnosis" in description
    assert "[Source: insurance_verification_policy.txt]" in result


def test_default_retriever_is_built_once_per_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    monkeypatch.setattr(retrieval, "build_retriever", lambda **kwargs: sentinel)

    first = retrieval._cached_default_retriever(3)
    second = retrieval._cached_default_retriever(3)

    assert first is sentinel
    assert second is sentinel
