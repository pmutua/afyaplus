"""FastAPI entry point for the AfyaPlus RAG Agent System."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, status
from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph

from app.agent.agent import create_agent
from app.agent.memory import thread_config
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import calculate_medication_volume, search_afyaplus_knowledge
from app.config import build_chat_model, load_settings
from app.models import ChatResponse, HealthResponse
from app.safeguards.middleware import PrivacyContext, protect_chat_request


def _production_agent() -> CompiledStateGraph:
    model = build_chat_model(load_settings())
    tools = [calculate_medication_volume, search_afyaplus_knowledge]
    return create_agent(model, tools, SYSTEM_PROMPT)


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


def create_app(agent: CompiledStateGraph | None = None) -> FastAPI:
    """Create the API, optionally using an injected agent graph for testing."""

    chat_agent = agent or _production_agent()
    application = FastAPI(title="AfyaPlus RAG Agent System", version="1.0.0")

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.post("/chat", response_model=ChatResponse)
    def chat(
        privacy: Annotated[PrivacyContext, Depends(protect_chat_request)],
    ) -> ChatResponse:
        try:
            result = chat_agent.invoke(
                {"messages": [("user", privacy.masked_message)]},
                thread_config(privacy.thread_id),
            )
            response = _latest_response(result)
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AfyaPlus assistant is temporarily unavailable.",
            ) from error
        return ChatResponse(
            response=privacy.restore_output(response),
            thread_id=privacy.thread_id,
        )

    return application


app = create_app()
