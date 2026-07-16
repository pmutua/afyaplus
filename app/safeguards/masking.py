"""Mask Kenyan PII (phone numbers, emails, AfyaPlus member/patient IDs)
before any text reaches a model call. Restoring the originals afterward is
demasking.py's job - see that module for the demask() half of the round trip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.safeguards.patterns import EMAIL_PATTERN, KENYAN_PHONE_PATTERN, MEMBER_ID_PATTERN


@dataclass(frozen=True)
class MaskResult:
    """Output of mask().

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


def mask(text: str) -> MaskResult:
    """Replace PII in `text` with placeholder tokens.

    Returns the masked text plus a vault mapping each token back to the
    original value it replaced.
    """

    vault: dict[str, str] = {}
    masked_text = _mask_pattern(text, KENYAN_PHONE_PATTERN, "PHONE", vault)
    masked_text = _mask_pattern(masked_text, EMAIL_PATTERN, "EMAIL", vault)
    masked_text = _mask_pattern(masked_text, MEMBER_ID_PATTERN, "MEMBER_ID", vault)
    return MaskResult(masked_text=masked_text, vault=vault)
