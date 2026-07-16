from typing import Any

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import PrivateAttr

from app.agent.agent import create_agent
from app.agent.memory import history_token_budget, thread_config


class RecordingFakeChatModel(FakeMessagesListChatModel):
    """Fake LangChain model that records messages after agent middleware."""

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


def test_preserves_history_per_thread_and_isolates_other_threads() -> None:
    model = FakeMessagesListChatModel(
        responses=[
            AIMessage(content="Karibu AfyaPlus."),
            AIMessage(content="Ninaendelea kukusaidia."),
            AIMessage(content="Karibu kwenye kikao kipya."),
        ]
    )
    agent = create_agent(model, [], "You are a test assistant.")
    session_a = thread_config("session-a")
    session_b = thread_config("session-b")

    agent.invoke({"messages": [("user", "Habari")]}, session_a)
    agent.invoke({"messages": [("user", "Endelea")]}, session_a)
    agent.invoke({"messages": [("user", "Habari")]}, session_b)

    session_a_messages = agent.get_state(session_a).values["messages"]
    session_b_messages = agent.get_state(session_b).values["messages"]
    assert len(session_a_messages) == 4
    assert len(session_b_messages) == 2


@pytest.mark.parametrize("thread_id", ["", "   "])
def test_rejects_empty_thread_id(thread_id: str) -> None:
    with pytest.raises(ValueError, match="thread_id must not be empty"):
        thread_config(thread_id)


def test_limits_model_history_but_retains_full_checkpoint_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_HISTORY_TOKEN_BUDGET", "20")
    model = RecordingFakeChatModel(
        responses=[AIMessage(content=f"Jibu la {turn}") for turn in range(1, 5)]
    )
    agent = create_agent(model, [], "You are a test assistant.")
    session = thread_config("bounded-session")

    for turn in range(1, 5):
        agent.invoke(
            {"messages": [("user", f"turn-{turn}-marker with several words")]},
            session,
        )

    final_model_input = " ".join(
        str(message.content) for message in model.recorded_messages[-1]
    )
    assert "turn-1-marker" not in final_model_input
    assert "turn-4-marker" in final_model_input
    assert len(agent.get_state(session).values["messages"]) == 8


@pytest.mark.parametrize("budget", ["0", "-1", "invalid"])
def test_rejects_invalid_history_token_budget(
    budget: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_HISTORY_TOKEN_BUDGET", budget)

    with pytest.raises(ValueError, match="AGENT_HISTORY_TOKEN_BUDGET"):
        history_token_budget()
