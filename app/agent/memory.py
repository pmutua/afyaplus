"""In-process conversation memory configuration for the AfyaPlus agent."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain_core.messages import trim_messages
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

DEFAULT_HISTORY_TOKEN_BUDGET = 2_048


def history_token_budget() -> int:
    """Return the positive token budget for history sent to the model."""

    raw_budget = os.getenv(
        "AGENT_HISTORY_TOKEN_BUDGET",
        str(DEFAULT_HISTORY_TOKEN_BUDGET),
    )
    try:
        budget = int(raw_budget)
    except ValueError as error:
        raise ValueError("AGENT_HISTORY_TOKEN_BUDGET must be an integer.") from error
    if budget <= 0:
        raise ValueError("AGENT_HISTORY_TOKEN_BUDGET must be greater than zero.")
    return budget


@wrap_model_call
def trim_conversation_history(
    request: ModelRequest[Any],
    handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
) -> ModelResponse[Any]:
    """Send only recent complete turns to the model within the token budget."""

    trimmed_messages = trim_messages(
        request.messages,
        max_tokens=history_token_budget(),
        token_counter="approximate",
        strategy="last",
        allow_partial=False,
        start_on="human",
        end_on=("human", "tool"),
    )
    return handler(request.override(messages=trimmed_messages))


def create_checkpointer() -> InMemorySaver:
    """Create a process-local checkpointer for conversation history."""

    return InMemorySaver()


def thread_config(thread_id: str) -> RunnableConfig:
    """Build the LangGraph config that isolates one conversation session."""

    normalized_id = thread_id.strip()
    if not normalized_id:
        raise ValueError("thread_id must not be empty.")
    return RunnableConfig(configurable={"thread_id": normalized_id})
