"""FastAPI privacy boundary for masking requests and restoring responses."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import ChatRequest
from app.safeguards.demasking import demask
from app.safeguards.masking import mask


@dataclass(frozen=True)
class PrivacyContext:
    """Request-local masked input and private placeholder vault."""

    masked_message: str
    thread_id: str
    _vault: dict[str, str] = field(repr=False)

    def restore_output(self, text: str) -> str:
        """Restore this request's PII immediately before returning output."""

        return demask(text, self._vault)


def protect_chat_request(request: ChatRequest) -> PrivacyContext:
    """Mask a validated chat request before route or agent processing."""

    masked = mask(request.message)
    return PrivacyContext(
        masked_message=masked.masked_text,
        thread_id=request.thread_id,
        _vault=masked.vault,
    )
