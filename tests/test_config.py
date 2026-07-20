import pytest

from app.config import (
    ConfigurationError,
    build_chat_model,
    build_fallback_settings,
    load_settings,
)

_CHAT_PROVIDER_VARS = (
    "MODEL_PROVIDER",
    "OLLAMA_LOCAL_BASE_URL",
    "OLLAMA_LOCAL_MODEL",
    "OLLAMA_LOCAL_API_KEY",
    "OLLAMA_CLOUD_BASE_URL",
    "OLLAMA_CLOUD_MODEL",
    "OLLAMA_CLOUD_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _CHAT_PROVIDER_VARS:
        monkeypatch.delenv(name, raising=False)
    # load_settings() calls load_dotenv() internally, which would otherwise
    # repopulate any var just deleted above from a developer's real .env -
    # tests must not depend on what happens to be configured locally.
    monkeypatch.setattr("app.config.load_dotenv", lambda *args, **kwargs: None)


def test_local_provider_uses_defaults_when_unconfigured() -> None:
    settings = load_settings()

    assert settings.provider == "ollama_local"
    assert settings.base_url == "http://localhost:11434/v1"
    assert settings.model == "llama3.2"
    assert settings.api_key == "ollama"


def test_local_provider_honors_explicit_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_LOCAL_BASE_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("OLLAMA_LOCAL_MODEL", "llama3.1")
    monkeypatch.setenv("OLLAMA_LOCAL_API_KEY", "custom-key")

    settings = load_settings()

    assert settings.base_url == "http://localhost:9999/v1"
    assert settings.model == "llama3.1"
    assert settings.api_key == "custom-key"


def test_cloud_provider_uses_configured_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")

    settings = load_settings()

    assert settings.provider == "ollama_cloud"
    assert settings.base_url == "https://ollama.com/v1"
    assert settings.model == "gpt-oss:120b"
    assert settings.api_key == "cloud-secret"


def test_cloud_provider_missing_api_key_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")

    with pytest.raises(ConfigurationError, match="OLLAMA_CLOUD_API_KEY"):
        load_settings()


def test_cloud_provider_missing_model_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")

    with pytest.raises(ConfigurationError, match="OLLAMA_CLOUD_MODEL"):
        load_settings()


def test_cloud_provider_invalid_url_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")
    monkeypatch.setenv("OLLAMA_CLOUD_BASE_URL", "not-a-url")

    with pytest.raises(ConfigurationError, match="OLLAMA_CLOUD_BASE_URL"):
        load_settings()


def test_invalid_provider_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "openrouter")

    with pytest.raises(ConfigurationError, match="MODEL_PROVIDER"):
        load_settings()


def test_factory_selection_switches_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    local_model = build_chat_model(load_settings())
    assert local_model.model_name == "llama3.2"
    assert local_model.openai_api_base == "http://localhost:11434/v1"

    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")
    cloud_model = build_chat_model(load_settings())

    assert cloud_model.model_name == "gpt-oss:120b"
    assert cloud_model.openai_api_base == "https://ollama.com/v1"


def test_chat_model_uses_zero_temperature_for_deterministic_answers() -> None:
    model = build_chat_model(load_settings())

    assert model.temperature == 0


def test_cloud_api_key_never_appears_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "super-secret-value")

    model = build_chat_model(load_settings())

    assert "super-secret-value" not in repr(model)
    assert "super-secret-value" not in str(model)


def test_no_fallback_available_when_cloud_is_not_configured() -> None:
    primary = load_settings()

    assert primary.provider == "ollama_local"
    assert build_fallback_settings(primary) is None


def test_fallback_resolves_to_cloud_when_local_is_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")
    primary = load_settings()

    fallback = build_fallback_settings(primary)

    assert primary.provider == "ollama_local"
    assert fallback is not None
    assert fallback.provider == "ollama_cloud"
    assert fallback.model == "gpt-oss:120b"


def test_fallback_resolves_to_local_when_cloud_is_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
    monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "cloud-secret")
    primary = load_settings()

    fallback = build_fallback_settings(primary)

    assert primary.provider == "ollama_cloud"
    assert fallback is not None
    assert fallback.provider == "ollama_local"
