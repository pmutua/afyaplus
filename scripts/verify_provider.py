"""Connectivity verification for the AfyaPlus model provider configuration.

Reports the active chat provider/model/host and the embedding
provider/model/host, then verifies each is actually reachable. Run it after
changing MODEL_PROVIDER, OLLAMA_LOCAL_*, OLLAMA_CLOUD_*, or the
OLLAMA_EMBEDDING_* variables to confirm the switch took effect.

Usage: python scripts/verify_provider.py

Never prints API keys, Authorization headers, or other secrets - only the
provider name, model name, and host.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import ConfigurationError, Settings, build_chat_model, load_settings  # noqa: E402
from app.rag.embeddings import build_embedding_model  # noqa: E402


def _redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***REDACTED***")
    return text


def _check_chat(settings: Settings) -> bool:
    print(f"[chat] provider:  {settings.provider}")
    print(f"[chat] model:     {settings.model}")
    print(f"[chat] host:      {settings.base_url}")
    try:
        build_chat_model(settings).invoke("ping")
    except Exception as error:  # noqa: BLE001 - reporting only, never re-raised
        message = _redact(str(error), settings.api_key)
        print(f"[chat] connection: FAILED ({type(error).__name__}: {message})")
        return False
    print("[chat] connection: OK")
    return True


def _check_embeddings() -> bool:
    provider = os.getenv("EMBEDDING_PROVIDER", "ollama_local")
    model = os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma")
    host = os.getenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434")
    print(f"[embedding] provider: {provider}")
    print(f"[embedding] model:    {model}")
    print(f"[embedding] host:     {host}")
    try:
        embedding_model = build_embedding_model()
        embedding_model.get_text_embedding("connectivity check")
    except Exception as error:  # noqa: BLE001 - reporting only, never re-raised
        print(f"[embedding] connection: FAILED ({type(error).__name__}: {error})")
        return False
    print("[embedding] connection: OK")
    return True


def main() -> int:
    try:
        settings = load_settings()
    except ConfigurationError as error:
        print(f"[chat] configuration error: {error}")
        return 1

    chat_ok = _check_chat(settings)
    print()
    embedding_ok = _check_embeddings()

    return 0 if chat_ok and embedding_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
