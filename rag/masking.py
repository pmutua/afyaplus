"""Privacy-compliance masking pipeline for the AfyaPlus RAG Agent System.

PrivacyCompliancePipeline masks Kenyan phone numbers, emails, and AfyaPlus
member/patient IDs, and restores them via demask(). Wiring this around the
full agent request/response cycle lands in SPEC-5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# +254 or a leading 0, then a Safaricom/Airtel/Telkom range (7XX or 1XX) and
# 8 more digits. Lookaround guards avoid matching inside a longer digit run
# (e.g. a member/patient ID) instead of a standalone phone number.
_KENYAN_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+254|0)[17]\d{8}(?!\d)")

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# AfyaPlus member/patient ID, e.g. AP-123456. Word boundaries keep this from
# matching a 6-digit slice out of a longer ID or a mid-word "AP-".
_MEMBER_ID_PATTERN = re.compile(r"\bAP-\d{6}\b")


@dataclass(frozen=True)
class MaskResult:
    """Output of PrivacyCompliancePipeline.mask().

    `vault` maps each placeholder token back to the original value it
    replaced, so demask() can restore it later without re-scanning the text.
    """

    masked_text: str
    vault: dict[str, str]


def _mask_pattern(text: str, pattern: re.Pattern[str], label: str, vault: dict[str, str]) -> str:
    """Replace every match of `pattern` in `text` with a unique placeholder token.

    Each original match is recorded in `vault` keyed by its placeholder token.
    """

    def _replace(match: re.Match[str]) -> str:
        token = f"<<{label}_{len(vault) + 1}>>"
        vault[token] = match.group(0)
        return token

    return pattern.sub(_replace, text)


class PrivacyCompliancePipeline:
    """Masks PII before a model call, and restores it after, via a token vault."""

    def mask(self, text: str) -> MaskResult:
        """Replace PII in `text` with placeholder tokens.

        Returns the masked text plus a vault mapping each token back to the
        original value it replaced.
        """

        vault: dict[str, str] = {}
        masked_text = _mask_pattern(text, _KENYAN_PHONE_PATTERN, "PHONE", vault)
        masked_text = _mask_pattern(masked_text, _EMAIL_PATTERN, "EMAIL", vault)
        masked_text = _mask_pattern(masked_text, _MEMBER_ID_PATTERN, "MEMBER_ID", vault)
        return MaskResult(masked_text=masked_text, vault=vault)

    def demask(self, text: str, vault: dict[str, str]) -> str:
        """Restore placeholder tokens in `text` to their original values using `vault`."""

        for token, original in vault.items():
            text = text.replace(token, original)
        return text
