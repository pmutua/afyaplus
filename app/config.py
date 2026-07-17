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

import logging
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, wrap_model_call
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = ("ollama_local", "ollama_cloud")
_OTHER_PROVIDER = {"ollama_local": "ollama_cloud", "ollama_cloud": "ollama_local"}


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


def build_fallback_settings(primary: Settings) -> Settings | None:
    """Resolve the *other* provider's settings as a fallback candidate.

    Returns None (not an error) when the other provider isn't fully
    configured - e.g. ollama_cloud without OLLAMA_CLOUD_MODEL/
    OLLAMA_CLOUD_API_KEY set. Local always has usable defaults, so it is
    always a valid fallback when cloud is primary; cloud is only a valid
    fallback when its required vars are present.
    """

    other = _OTHER_PROVIDER[primary.provider]
    try:
        return _cloud_settings() if other == "ollama_cloud" else _local_settings()
    except ConfigurationError:
        return None


def build_fallback_middleware(primary: Settings) -> AgentMiddleware | None:
    """Build agent middleware that retries a failed chat call on the other provider.

    Explicit and loudly logged, not silent: this is a deliberate exception to
    "never silently fall back to another provider" (see module docstring) -
    a fallback only ever happens when the other provider is fully configured,
    and always logs a warning naming both providers so it's never ambiguous
    which one actually served a given request. If no fallback is available,
    or the fallback attempt also fails, the original exception propagates
    unchanged (the existing FastAPI 503 behavior for a fully-failed request
    is untouched).
    """

    fallback_settings = build_fallback_settings(primary)
    if fallback_settings is None:
        return None
    fallback_model = build_chat_model(fallback_settings)

    @wrap_model_call
    def _fallback_on_failure(
        request: ModelRequest[Any],
        handler: Any,
    ) -> ModelResponse[Any]:
        try:
            return handler(request)
        except Exception:
            logger.warning(
                "Chat provider %r failed; falling back to %r.",
                primary.provider,
                fallback_settings.provider,
            )
            return handler(request.override(model=fallback_model))

    return _fallback_on_failure
