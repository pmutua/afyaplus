import pytest

from app.rag import embeddings

_ENV_VARS = (
    "EMBEDDING_PROVIDER",
    "OLLAMA_EMBEDDING_BASE_URL",
    "MODEL_PROVIDER",
    "OLLAMA_CLOUD_BASE_URL",
    "OLLAMA_CLOUD_MODEL",
    "OLLAMA_CLOUD_API_KEY",
    "CI",
)


@pytest.fixture(autouse=True)
def _clean_embedding_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_embedding_host_defaults_to_local_ollama() -> None:
    assert embeddings._ollama_host() == "http://localhost:11434"


def test_embedding_host_strips_v1_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_EMBEDDING_BASE_URL", "http://example.com:11434/v1")

    assert embeddings._ollama_host() == "http://example.com:11434"


def test_embedding_host_independent_of_cloud_chat_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching the chat provider to ollama_cloud must not move embeddings off-machine."""

    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_BASE_URL", "https://ollama.com/v1")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")

    assert embeddings._ollama_host() == "http://localhost:11434"


def test_unsupported_embedding_provider_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama_cloud")

    with pytest.raises(RuntimeError, match="EMBEDDING_PROVIDER"):
        embeddings.build_embedding_model()


def test_ci_short_circuit_wins_over_an_invalid_embedding_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama_cloud")

    model = embeddings.build_embedding_model()

    assert isinstance(model, embeddings.DeterministicHashEmbedding)


def test_fastembed_local_provider_is_dispatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMBEDDING_PROVIDER=fastembed_local routes to the in-process backend.

    Monkeypatches _fastembed_embedding rather than letting it run for real -
    a real call downloads an ONNX model on first use, unsuitable for a fast
    unit test (same reason _ollama_embedding is never exercised for real
    here either).
    """

    monkeypatch.setenv("EMBEDDING_PROVIDER", "fastembed_local")
    sentinel = object()
    monkeypatch.setattr(embeddings, "_fastembed_embedding", lambda: sentinel)

    assert embeddings.build_embedding_model() is sentinel
