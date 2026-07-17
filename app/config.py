"""Environment configuration and model provider factory for the AfyaPlus RAG agent.

MODEL_PROVIDER selects the chat transport: "ollama_local" (default) or
"ollama_cloud". build_chat_model() is the single factory the rest of the
application calls - it returns a langchain ChatOpenAI instance wired to
whichever provider is configured, and callers never branch on which one is
active.

Chat and embeddings are configured independently: switching MODEL_PROVIDER
to "ollama_cloud" does not change where embeddings run (see
app/rag/embeddings.py) - that stays local unless EMBEDDING_PROVIDER is
explicitly changed, so document text is never sent off-machine as a side
effect of a chat provider switch.

The OPENROUTER_API_KEY/OPENAI_API_KEY/MODEL_BASE_URL/CLOUD_MODEL and
unprefixed OLLAMA_BASE_URL/OLLAMA_MODEL/OLLAMA_API_KEY variables belong to
the separate Triage Engine capability (triage/engine.py) and are
intentionally not read here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

_VALID_PROVIDERS = ("ollama_local", "ollama_cloud")


class ConfigurationError(RuntimeError):
    """Raised when MODEL_PROVIDER configuration is invalid or incomplete."""


@dataclass(frozen=True)
class Settings:
    """Resolved chat-model settings for whichever provider is active."""

    provider: str
    base_url: str
    model: str
    api_key: str
    timeout_seconds: float


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(f"{name} is required when using this provider but is not set.")
    return value


def _require_url(name: str, value: str) -> str:
    if not value.startswith(("http://", "https://")):
        raise ConfigurationError(f"{name} must be an http(s) URL, got {value!r}.")
    return value


def _local_settings() -> Settings:
    base_url = os.getenv("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434/v1")
    return Settings(
        provider="ollama_local",
        base_url=_require_url("OLLAMA_LOCAL_BASE_URL", base_url),
        model=os.getenv("OLLAMA_LOCAL_MODEL") or "llama3.2",
        api_key=os.getenv("OLLAMA_LOCAL_API_KEY") or "ollama",
        timeout_seconds=float(os.getenv("LOCAL_TIMEOUT_SECONDS", "20.0")),
    )


def _cloud_settings() -> Settings:
    base_url = os.getenv("OLLAMA_CLOUD_BASE_URL", "https://ollama.com/v1")
    return Settings(
        provider="ollama_cloud",
        base_url=_require_url("OLLAMA_CLOUD_BASE_URL", base_url),
        model=_require_env("OLLAMA_CLOUD_MODEL"),
        api_key=_require_env("OLLAMA_CLOUD_API_KEY"),
        timeout_seconds=float(os.getenv("CLOUD_TIMEOUT_SECONDS", "30.0")),
    )


def load_settings() -> Settings:
    """Load chat-model settings from .env, failing fast on bad configuration."""

    load_dotenv()
    provider = os.getenv("MODEL_PROVIDER", "ollama_local")
    if provider not in _VALID_PROVIDERS:
        raise ConfigurationError(
            f"MODEL_PROVIDER={provider!r} is invalid. Must be one of {_VALID_PROVIDERS}."
        )
    if provider == "ollama_cloud":
        return _cloud_settings()
    return _local_settings()


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """Provider factory: build the chat client for whichever provider is active.

    Both providers speak the OpenAI-compatible API (Ollama's local and cloud
    endpoints both do), so the same ChatOpenAI wiring serves either one -
    callers only ever see a BaseChatModel and never branch on the provider.
    """

    return ChatOpenAI(
        model=settings.model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=settings.timeout_seconds,
        temperature=0,
    )
