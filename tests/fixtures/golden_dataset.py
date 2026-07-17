"""Golden question/answer cases for grounding and retrieval compliance tests.

Each case is answerable (or deliberately not answerable) from
tests/fixtures/knowledge_base/, independent of the real knowledge/ directory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenCase:
    """One golden retrieval case checked against the fixture knowledge base."""

    id: str
    question: str
    expect_grounded: bool
    expected_source: str | None = None
    required_answer_keywords: tuple[str, ...] = ()


GOLDEN_DATASET: tuple[GoldenCase, ...] = (
    GoldenCase(
        id="dental_checkup_count",
        question="How many dental check-ups does AfyaPlus cover per year?",
        expect_grounded=True,
        expected_source="afyaplus_test_policy.txt",
        required_answer_keywords=("two", "check-ups"),
    ),
    GoldenCase(
        id="orthodontic_preauthorization",
        question="Does orthodontic treatment need pre-authorization?",
        expect_grounded=True,
        expected_source="afyaplus_test_policy.txt",
        required_answer_keywords=("pre-authorization",),
    ),
    GoldenCase(
        id="fracture_routing",
        question="Where should a suspected fracture be routed?",
        expect_grounded=True,
        expected_source="clinical_test_protocol.txt",
        required_answer_keywords=("emergency facility",),
    ),
    GoldenCase(
        id="unrelated_question",
        question="What is the boiling point of water?",
        expect_grounded=False,
    ),
)


def load_golden_dataset() -> tuple[GoldenCase, ...]:
    """Return the golden retrieval/grounding compliance cases."""

    return GOLDEN_DATASET
