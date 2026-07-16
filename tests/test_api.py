from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agent.agent import create_agent
from app.agent.memory import thread_config
from app.main import create_app


def test_health_endpoint_returns_ok() -> None:
    agent = create_agent(
        FakeMessagesListChatModel(responses=[AIMessage(content="Ready")]),
        [],
        "You are a test assistant.",
    )
    response = TestClient(create_app(agent)).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_masks_model_input_and_demasks_final_response() -> None:
    agent = create_agent(
        FakeMessagesListChatModel(
            responses=[AIMessage(content="Member <<MEMBER_ID_1>> is under review.")]
        ),
        [],
        "You are a test assistant.",
    )
    client = TestClient(create_app(agent))

    response = client.post(
        "/chat",
        json={"message": "Check member AP-123456", "thread_id": "session-254"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "response": "Member AP-123456 is under review.",
        "thread_id": "session-254",
    }
    messages = agent.get_state(thread_config("session-254")).values["messages"]
    assert "AP-123456" not in messages[0].content
    assert "<<MEMBER_ID_1>>" in messages[0].content


def test_chat_rejects_invalid_thread_id() -> None:
    agent = create_agent(
        FakeMessagesListChatModel(responses=[AIMessage(content="Ready")]),
        [],
        "You are a test assistant.",
    )
    response = TestClient(create_app(agent)).post(
        "/chat",
        json={"message": "Habari", "thread_id": "contains spaces"},
    )

    assert response.status_code == 422
