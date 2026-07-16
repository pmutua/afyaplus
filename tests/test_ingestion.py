from pathlib import Path

import pytest

from app.rag.ingestion import build_index


def test_reloads_persisted_index_without_source_reingestion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI", "true")
    knowledge_dir = tmp_path / "knowledge"
    storage_dir = tmp_path / "chroma"
    knowledge_dir.mkdir()
    source_file = knowledge_dir / "policy.txt"
    source_file.write_text(
        "AfyaPlus maternity cover has a six-month waiting period.",
        encoding="utf-8",
    )

    build_index(knowledge_dir, storage_dir, "persistence_test")
    source_file.unlink()
    reloaded_index = build_index(knowledge_dir, storage_dir, "persistence_test")

    results = reloaded_index.as_retriever(similarity_top_k=1).retrieve(
        "maternity waiting period"
    )
    assert len(results) == 1
    assert "six-month waiting period" in results[0].text
