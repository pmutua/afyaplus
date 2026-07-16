"""LangChain agent construction for the AfyaPlus RAG Agent System."""

from __future__ import annotations

from collections.abc import Sequence

from langchain.agents import create_agent as create_langchain_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph


def create_agent(
    model: str | BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
) -> CompiledStateGraph:
    """Create the stateless agent graph; memory is added in SPEC-4.2."""

    return create_langchain_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
    )
