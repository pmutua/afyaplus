"""Chainlit browser interface for the AfyaPlus RAG Agent System."""

from __future__ import annotations

from uuid import uuid4

import chainlit as cl
from pydantic import ValidationError

from app.chat import run_chat
from app.models import ChatRequest
from app.safeguards.rate_limiting import (
    InMemoryRateLimiter,
    load_rate_limit_settings,
    retry_message,
)

THREAD_ID_KEY = "afyaplus_thread_id"
UNAVAILABLE_MESSAGE = "The AfyaPlus assistant is temporarily unavailable."
UI_RATE_LIMITER = InMemoryRateLimiter(load_rate_limit_settings())


def _new_thread_id() -> str:
    return f"ui-{uuid4().hex}"


def _session_thread_id() -> str:
    thread_id = cl.user_session.get(THREAD_ID_KEY)
    if isinstance(thread_id, str):
        return thread_id
    thread_id = _new_thread_id()
    cl.user_session.set(THREAD_ID_KEY, thread_id)
    return thread_id


def _ui_rate_limit_message(
    thread_id: str,
    limiter: InMemoryRateLimiter = UI_RATE_LIMITER,
) -> str | None:
    decision = limiter.check(f"ui:{thread_id}")
    if decision.allowed:
        return None
    return retry_message(decision.retry_after_seconds)


@cl.on_chat_start
async def start_chat() -> None:
    """Create an isolated memory thread and greet the user."""

    cl.user_session.set(THREAD_ID_KEY, _new_thread_id())
    await cl.Message(
        content="Karibu AfyaPlus. How can I help you today?",
        author="AfyaPlus",
    ).send()


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """Send a UI turn through the same privacy boundary as the API."""

    try:
        request = ChatRequest(
            message=message.content,
            thread_id=_session_thread_id(),
        )
    except ValidationError:
        await cl.Message(
            content="Please enter a message between 1 and 8,000 characters.",
            author="AfyaPlus",
        ).send()
        return

    limited_message = _ui_rate_limit_message(request.thread_id)
    if limited_message is not None:
        await cl.Message(content=limited_message, author="AfyaPlus").send()
        return

    try:
        response = await cl.make_async(run_chat)(request)
    except Exception:
        await cl.Message(content=UNAVAILABLE_MESSAGE, author="AfyaPlus").send()
        return
    await cl.Message(content=response.response, author="AfyaPlus").send()
