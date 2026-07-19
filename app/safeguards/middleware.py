"""FastAPI privacy boundary for masking requests and restoring responses."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.models import ChatRequest
from app.safeguards.demasking import demask
from app.safeguards.masking import mask

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrivacyContext:
    """Request-local masked input and private placeholder vault."""

    masked_message: str
    thread_id: str
    _vault: dict[str, str] = field(repr=False)

    def restore_output(self, text: str) -> str:
        """Restore this request's PII immediately before returning output."""

        restored_count = sum(1 for token in self._vault if token in text)
        if restored_count:
            logger.info(
                "Restored %d placeholder(s) for thread %s.",
                restored_count,
                self.thread_id,
            )
        return demask(text, self._vault)


def protect_chat_request(request: ChatRequest) -> PrivacyContext:
    """Mask a validated chat request before route or agent processing.

    Logs the masked message (never the raw one) so a reviewer watching
    application logs can directly confirm PII never reaches a model call -
    e.g. seeing "Call me at <<PHONE_1>>" rather than a real phone number.
    """

    masked = mask(request.message)
    if masked.vault:
        logger.info(
            "Masked %d PII item(s) for thread %s: %s",
            len(masked.vault),
            request.thread_id,
            masked.masked_text,
        )
    return PrivacyContext(
        masked_message=masked.masked_text,
        thread_id=request.thread_id,
        _vault=masked.vault,
    )
