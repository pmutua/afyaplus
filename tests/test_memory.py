import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agent.agent import create_agent
from app.agent.memory import thread_config


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
