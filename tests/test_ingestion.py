from pathlib import Path

import pytest

from app.rag.ingestion import ingest_knowledge
from tests.qdrant_fakes import FakeQdrantClient


@pytest.fixture
def qdrant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "https://test.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "test-api-key")


def test_reuses_populated_collection_without_source_reingestion(
    tmp_path: Path,
    qdrant_env: None,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    source_file = knowledge_dir / "policy.txt"
    source_file.write_text(
        "AfyaPlus maternity cover has a six-month waiting period.",
        encoding="utf-8",
    )
    client = FakeQdrantClient()

    first = ingest_knowledge(knowledge_dir, "persistence_test", client)
    source_file.unlink()
    second = ingest_knowledge(knowledge_dir, "persistence_test", client)

    assert first.indexed_nodes == 1
    assert first.reused_existing is False
    assert second.indexed_nodes == 0
    assert second.reused_existing is True


def test_uploads_text_and_source_metadata_for_managed_inference(
    tmp_path: Path,
    qdrant_env: None,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "routing.txt").write_text(
        "Route emergency breathing cases to urgent clinical review.",
        encoding="utf-8",
    )
    client = FakeQdrantClient()

    result = ingest_knowledge(knowledge_dir, "payload_test", client)

    point = client.points[0]
    assert result.indexed_nodes == 1
    assert point.vector.model == "sentence-transformers/all-MiniLM-L6-v2"
    assert point.payload["metadata"] == {"file_name": "routing.txt"}
