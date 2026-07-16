"""Restore placeholder tokens produced by masking.py's mask() back to their
original values, right before the final result is shown to a user.
"""

from __future__ import annotations


def demask(text: str, vault: dict[str, str]) -> str:
    """Restore placeholder tokens in `text` to their original values using `vault`."""

    for token, original in vault.items():
        text = text.replace(token, original)
    return text
