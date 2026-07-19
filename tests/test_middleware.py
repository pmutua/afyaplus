"""Tests for the request-local FastAPI privacy boundary."""

import logging

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


def test_masking_is_logged_with_redacted_text_only(caplog) -> None:
    raw_phone = "+254712345678"

    with caplog.at_level(logging.INFO, logger="app.safeguards.middleware"):
        privacy = protect_chat_request(
            ChatRequest(message=f"Call {raw_phone}", thread_id="log-test-001")
        )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "log-test-001" in log_text
    assert privacy.masked_message in log_text
    assert raw_phone not in log_text


def test_no_masking_log_emitted_when_no_pii_present(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.safeguards.middleware"):
        protect_chat_request(
            ChatRequest(message="No PII in this message.", thread_id="log-test-002")
        )

    assert caplog.records == []


def test_restore_output_logs_a_count_never_the_restored_pii(caplog) -> None:
    raw_email = "patient@example.com"
    privacy = protect_chat_request(
        ChatRequest(message=f"Reach me at {raw_email}", thread_id="log-test-003")
    )
    caplog.clear()

    with caplog.at_level(logging.INFO, logger="app.safeguards.middleware"):
        restored = privacy.restore_output("Noted, will contact <<EMAIL_1>>.")

    assert restored == f"Noted, will contact {raw_email}."
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "1" in log_text
    assert "log-test-003" in log_text
    assert raw_email not in log_text
