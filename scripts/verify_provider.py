"""Connectivity verification for the AfyaPlus model provider configuration.

Reports the active chat provider/model/host and Qdrant collection/model/host,
then verifies each is reachable. Run it after changing MODEL_PROVIDER,
OLLAMA_LOCAL_*, OLLAMA_CLOUD_*, or QDRANT_* variables.

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
from app.rag.vector_store import open_vector_store  # noqa: E402


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


def _check_qdrant() -> bool:
    host = os.getenv("QDRANT_URL", "<not configured>")
    model = os.getenv(
        "QDRANT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    collection = os.getenv("QDRANT_COLLECTION_NAME", "afyaplus_knowledge_base")
    print(f"[qdrant] host:       {host}")
    print(f"[qdrant] collection: {collection}")
    print(f"[qdrant] model:      {model}")
    try:
        handle = open_vector_store()
    except Exception as error:  # noqa: BLE001 - reporting only, never re-raised
        api_key = os.getenv("QDRANT_API_KEY", "")
        message = _redact(str(error), api_key)
        print(f"[qdrant] connection: FAILED ({type(error).__name__}: {message})")
        return False
    state = "populated" if handle.has_nodes else "empty"
    print(f"[qdrant] connection: OK ({state} collection)")
    return True


def main() -> int:
    try:
        settings = load_settings()
    except ConfigurationError as error:
        print(f"[chat] configuration error: {error}")
        return 1

    chat_ok = _check_chat(settings)
    print()
    qdrant_ok = _check_qdrant()

    return 0 if chat_ok and qdrant_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
