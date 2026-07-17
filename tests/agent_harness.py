"""Shared end-to-end agent test harness for compliance test suites.

Wires the real agent (real tools, real grounding/masking) to the fixture
knowledge base in tests/fixtures/knowledge_base, so later compliance test
suites can drive full agent turns without any live network call to Qdrant
Cloud or Ollama Cloud.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from app.agent.agent import create_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import calculate_medication_volume, search_afyaplus_knowledge
from app.rag.retrieval import query_knowledge
from tests.qdrant_fakes import FakeQdrantClient

FIXTURE_KNOWLEDGE_DIR = Path(__file__).parent / "fixtures" / "knowledge_base"
FIXTURE_COLLECTION_NAME = "compliance_fixture_knowledge_base"


class ScriptedToolCallingChatModel(FakeMessagesListChatModel):
    """A scripted fake chat model usable with a real, tool-bound agent.

    FakeMessagesListChatModel.bind_tools raises NotImplementedError (the
    base BaseChatModel default), so it cannot back an agent built with real
    tools. Accepting the bind and returning canned responses regardless is
    enough for compliance tests that never need the model to actually choose
    a tool call.
    """

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        return self


def set_fixture_qdrant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the env vars vector_store.py requires, even when using a fake client."""

    monkeypatch.setenv("QDRANT_URL", "https://compliance-fixture.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "compliance-fixture-api-key")


def fixture_query_knowledge(question: str) -> str:
    """Run real retrieval and grounding against the fixture knowledge base."""

    return query_knowledge(
        question,
        knowledge_dir=FIXTURE_KNOWLEDGE_DIR,
        collection_name=FIXTURE_COLLECTION_NAME,
        client=FakeQdrantClient(),
    )


def build_fixture_agent(
    monkeypatch: pytest.MonkeyPatch,
    model: ScriptedToolCallingChatModel,
    extra_tools: Sequence[BaseTool] = (),
) -> CompiledStateGraph:
    """Build a full agent whose knowledge tool is bound to fixture data.

    Routes search_afyaplus_knowledge through fixture_query_knowledge instead
    of the real Qdrant-backed default retriever, so compliance tests exercise
    real masking, grounding, and tool logic without a live network call.
    """

    set_fixture_qdrant_env(monkeypatch)
    monkeypatch.setattr(
        "app.agent.tools.knowledge.query_knowledge", fixture_query_knowledge
    )
    tools = [calculate_medication_volume, search_afyaplus_knowledge, *extra_tools]
    return create_agent(model, tools, SYSTEM_PROMPT)
