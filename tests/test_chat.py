"""Tests for the chat service shared by FastAPI and Chainlit."""

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler, CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import PrivateAttr

from app.agent.agent import create_agent
from app.chat import run_chat
from app.models import ChatRequest


class RecordingChatModel(FakeMessagesListChatModel):
    """Capture the messages delivered across the shared chat boundary."""

    _recorded_messages: list[list[BaseMessage]] = PrivateAttr(default_factory=list)

    @property
    def recorded_messages(self) -> list[list[BaseMessage]]:
        return self._recorded_messages

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self._recorded_messages.append(list(messages))
        return super()._generate(messages, stop, run_manager, **kwargs)


def test_shared_chat_masks_input_and_restores_output() -> None:
    raw_phone = "+254712345678"
    model = RecordingChatModel(
        responses=[AIMessage(content="I will contact <<PHONE_1>>.")]
    )
    agent = create_agent(model, [], "You are a test assistant.")

    response = run_chat(
        ChatRequest(message=f"Call me at {raw_phone}.", thread_id="ui-test-254"),
        agent,
    )

    model_input = " ".join(
        str(message.content) for message in model.recorded_messages[0]
    )
    assert raw_phone not in model_input
    assert "<<PHONE_1>>" in model_input
    assert response.response == f"I will contact {raw_phone}."
    assert response.thread_id == "ui-test-254"


def test_run_chat_attaches_callbacks_to_agent_invocation() -> None:
    class RecordingCallbackHandler(BaseCallbackHandler):
        def __init__(self) -> None:
            self.chain_starts = 0

        def on_chain_start(self, *args: Any, **kwargs: Any) -> None:
            self.chain_starts += 1

    model = RecordingChatModel(responses=[AIMessage(content="Ready to help.")])
    agent = create_agent(model, [], "You are a test assistant.")
    handler = RecordingCallbackHandler()

    run_chat(
        ChatRequest(message="Hello there", thread_id="ui-test-256"),
        agent,
        callbacks=[handler],
    )

    assert handler.chain_starts > 0
