import pytest

from app.rag.embeddings import inference_document, load_inference_config


def test_defaults_to_free_qdrant_minilm_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QDRANT_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("QDRANT_EMBEDDING_DIMENSIONS", raising=False)

    config = load_inference_config()

    assert config.model == "sentence-transformers/all-MiniLM-L6-v2"
    assert config.dimensions == 384


def test_rejects_non_positive_embedding_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_EMBEDDING_DIMENSIONS", "0")

    with pytest.raises(RuntimeError, match="must be positive"):
        load_inference_config()


def test_builds_managed_inference_document() -> None:
    config = load_inference_config()

    document = inference_document("AfyaPlus member verification", config)

    assert document.text == "AfyaPlus member verification"
    assert document.model == config.model
