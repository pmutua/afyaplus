"""Privacy-compliance masking pipeline for the AfyaPlus RAG Agent System.

Scaffolding only: PrivacyCompliancePipeline defines the mask/demask contract.
Regex-based PII detection (Kenyan phone numbers, emails, member/patient IDs)
lands in the following SPEC-1 tasks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaskResult:
    """Output of PrivacyCompliancePipeline.mask().

    `vault` maps each placeholder token back to the original value it
    replaced, so demask() can restore it later without re-scanning the text.
    """

    masked_text: str
    vault: dict[str, str]


class PrivacyCompliancePipeline:
    """Masks PII before a model call, and restores it after, via a token vault."""

    def mask(self, text: str) -> MaskResult:
        """Replace PII in `text` with placeholder tokens.

        Returns the masked text plus a vault mapping each token back to the
        original value it replaced.
        """

        raise NotImplementedError

    def demask(self, text: str, vault: dict[str, str]) -> str:
        """Restore placeholder tokens in `text` to their original values using `vault`."""

        raise NotImplementedError
