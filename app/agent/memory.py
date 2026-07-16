"""In-process conversation memory configuration for the AfyaPlus agent."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver


def create_checkpointer() -> InMemorySaver:
    """Create a process-local checkpointer for conversation history."""

    return InMemorySaver()


def thread_config(thread_id: str) -> RunnableConfig:
    """Build the LangGraph config that isolates one conversation session."""

    normalized_id = thread_id.strip()
    if not normalized_id:
        raise ValueError("thread_id must not be empty.")
    return RunnableConfig(configurable={"thread_id": normalized_id})
