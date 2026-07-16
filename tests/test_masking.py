"""Unit tests for app.safeguards.masking.mask() (SPEC-1.6)."""

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

CLINICAL_ONLY_TEXT = (
    "Patient reports severe headache for two days and sudden swelling of "
    "the feet at 7 months pregnant. No PII present in this message."
)


def test_all_known_pii_variants_are_detected():
    for text in PII_CASES:
        result = mask(text)
        assert result.vault, f"expected at least one PII match in: {text!r}"


def test_masked_text_never_contains_raw_pii():
    for text in PII_CASES:
        result = mask(text)
        for raw_value in result.vault.values():
            assert raw_value not in result.masked_text


def test_clinical_context_survives_masking_unmangled():
    result = mask(CLINICAL_ONLY_TEXT)
    assert result.masked_text == CLINICAL_ONLY_TEXT
    assert result.vault == {}


def test_clinical_context_preserved_alongside_masked_pii():
    text = (
        "Patient AP-123456 reports severe headache and swelling; reachable "
        "at 0798765432 or patient@example.com for follow-up."
    )
    result = mask(text)
    assert "severe headache and swelling" in result.masked_text
    assert "reachable at" in result.masked_text
    assert "for follow-up" in result.masked_text
