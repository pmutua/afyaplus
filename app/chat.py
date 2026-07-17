"""Shared privacy-safe chat execution for API and browser interfaces."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph

from app.agent.agent import create_agent
from app.agent.memory import thread_config
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import calculate_medication_volume, search_afyaplus_knowledge
from app.config import build_chat_model, build_fallback_middleware, load_settings
from app.models import ChatRequest, ChatResponse
from app.safeguards.middleware import protect_chat_request


@lru_cache(maxsize=1)
def production_agent() -> CompiledStateGraph:
    """Build and reuse the process-level production agent graph."""

    settings = load_settings()
    model = build_chat_model(settings)
    tools = [calculate_medication_volume, search_afyaplus_knowledge]
    fallback = build_fallback_middleware(settings)
    middleware = [fallback] if fallback is not None else []
    return create_agent(model, tools, SYSTEM_PROMPT, middleware)


def _message_text(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    text_blocks = [
        block.get("text", "")
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "".join(text_blocks)


def _latest_response(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    if not messages or not isinstance(messages[-1], BaseMessage):
        raise ValueError("Agent returned no response message.")
    response = _message_text(messages[-1]).strip()
    if not response:
        raise ValueError("Agent returned an empty response.")
    return response


def run_chat(
    request: ChatRequest,
    agent: CompiledStateGraph | None = None,
) -> ChatResponse:
    """Run one validated turn through masking, the agent, and de-masking."""

    privacy = protect_chat_request(request)
    chat_agent = agent or production_agent()
    result = chat_agent.invoke(
        {"messages": [("user", privacy.masked_message)]},
        thread_config(privacy.thread_id),
    )
    response = _latest_response(result)
    return ChatResponse(
        response=privacy.restore_output(response),
        thread_id=privacy.thread_id,
    )
