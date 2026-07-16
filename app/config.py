"""Environment configuration for the served AfyaPlus RAG agent."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the local Ollama chat model."""

    ollama_base_url: str
    ollama_model: str
    ollama_api_key: str
    timeout_seconds: float


def load_settings() -> Settings:
    """Load settings from .env with deterministic local defaults."""

    load_dotenv()
    return Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        ollama_api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        timeout_seconds=float(os.getenv("LOCAL_TIMEOUT_SECONDS", "20.0")),
    )


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """Build LangChain's chat client over Ollama's OpenAI-compatible endpoint."""

    return ChatOpenAI(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        timeout=settings.timeout_seconds,
        temperature=0,
    )
