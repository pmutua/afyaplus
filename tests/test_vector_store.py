import pytest
from qdrant_client import models

from app.rag.vector_store import load_qdrant_settings, open_vector_store
from tests.qdrant_fakes import FakeQdrantClient


def test_requires_qdrant_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="QDRANT_URL"):
        load_qdrant_settings()


def test_creates_cosine_collection_for_inference_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_URL", "https://test.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "test-api-key")
    client = FakeQdrantClient()

    handle = open_vector_store("afyaplus_test", client)

    params = client.created_kwargs["vectors_config"]
    assert handle.has_nodes is False
    assert params.size == 384
    assert params.distance == models.Distance.COSINE
    assert client.created_kwargs["metadata"]["embedding_model"].endswith(
        "all-MiniLM-L6-v2"
    )
