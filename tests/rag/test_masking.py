"""Unit tests for rag.masking.PrivacyCompliancePipeline (SPEC-1.6)."""

from rag.masking import PrivacyCompliancePipeline

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


def test_round_trip_restores_original_text():
    pipeline = PrivacyCompliancePipeline()
    for text in PII_CASES:
        result = pipeline.mask(text)
        assert pipeline.demask(result.masked_text, result.vault) == text


def test_all_known_pii_variants_are_detected():
    pipeline = PrivacyCompliancePipeline()
    for text in PII_CASES:
        result = pipeline.mask(text)
        assert result.vault, f"expected at least one PII match in: {text!r}"


def test_masked_text_never_contains_raw_pii():
    pipeline = PrivacyCompliancePipeline()
    for text in PII_CASES:
        result = pipeline.mask(text)
        for raw_value in result.vault.values():
            assert raw_value not in result.masked_text


def test_clinical_context_survives_masking_unmangled():
    pipeline = PrivacyCompliancePipeline()
    result = pipeline.mask(CLINICAL_ONLY_TEXT)
    assert result.masked_text == CLINICAL_ONLY_TEXT
    assert result.vault == {}


def test_clinical_context_preserved_alongside_masked_pii():
    pipeline = PrivacyCompliancePipeline()
    text = (
        "Patient AP-123456 reports severe headache and swelling; reachable "
        "at 0798765432 or patient@example.com for follow-up."
    )
    result = pipeline.mask(text)
    assert "severe headache and swelling" in result.masked_text
    assert "reachable at" in result.masked_text
    assert "for follow-up" in result.masked_text
