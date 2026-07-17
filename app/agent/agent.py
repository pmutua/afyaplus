"""LangChain agent construction for the AfyaPlus RAG Agent System."""

from __future__ import annotations

from collections.abc import Sequence

from langchain.agents import create_agent as create_langchain_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from app.agent.memory import create_checkpointer, trim_conversation_history


def create_agent(
    model: str | BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
    middleware: Sequence[AgentMiddleware] = (),
) -> CompiledStateGraph:
    """Create an agent graph with isolated in-process conversation memory.

    middleware is appended after trim_conversation_history (e.g. the
    optional chat-provider fallback from app.config.build_fallback_middleware)
    - empty by default so existing callers are unaffected.
    """

    return create_langchain_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        checkpointer=create_checkpointer(),
        middleware=[trim_conversation_history, *middleware],
    )
