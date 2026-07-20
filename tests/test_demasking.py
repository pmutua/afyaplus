"""Unit tests for app.safeguards.demasking.demask() (SPEC-1.6)."""

from app.safeguards.demasking import demask
from app.safeguards.masking import mask

PII_CASES = [
    "Call me at +254712345678 about my appointment.",
    "Call me at 0712345678 about my appointment.",
    "Reach me at 0112345678 for a callback.",
    "My email is patient@example.com for follow-up.",
    "My patient ID is AP-123456 for insurance verification.",
    (
        "My patient ID is AP-123456, email patient@example.com, "
        "phone 0798765432, regarding severe headache and swelling."
    ),
]


def test_round_trip_restores_original_text():
    for text in PII_CASES:
        result = mask(text)
        assert demask(result.masked_text, result.vault) == text
