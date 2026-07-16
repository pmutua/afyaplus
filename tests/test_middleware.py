"""Tests for the request-local FastAPI privacy boundary."""

from app.models import ChatRequest
from app.safeguards.middleware import protect_chat_request


def test_masks_request_pii_and_restores_only_approved_output() -> None:
    request = ChatRequest(
        message="Email aisha@example.co.ke or call +254712345678 for AP-123456.",
        thread_id="privacy-session-254",
    )

    privacy = protect_chat_request(request)

    assert "aisha@example.co.ke" not in privacy.masked_message
    assert "+254712345678" not in privacy.masked_message
    assert "AP-123456" not in privacy.masked_message
    assert privacy.restore_output(
        "Contact <<EMAIL_2>> or <<PHONE_1>> about <<MEMBER_ID_3>>."
    ) == "Contact aisha@example.co.ke or +254712345678 about AP-123456."


def test_privacy_context_repr_excludes_raw_pii_vault() -> None:
    raw_email = "patient@example.com"

    privacy = protect_chat_request(
        ChatRequest(message=f"Contact {raw_email}", thread_id="private-repr")
    )

    assert raw_email not in repr(privacy)
