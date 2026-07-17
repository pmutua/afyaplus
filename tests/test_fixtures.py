"""Self-consistency checks for the compliance test seams (fixtures + harness).

Guards against a later compliance-test part silently building on a malformed
golden dataset, malicious-prompt dataset, or a broken fixture-knowledge-base
wiring.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from app.models import ChatRequest
from app.chat import run_chat
from app.rag.grounding import NOT_FOUND_RESPONSE
from tests.agent_harness import (
    FIXTURE_KNOWLEDGE_DIR,
    ScriptedToolCallingChatModel,
    build_fixture_agent,
    fixture_query_knowledge,
    set_fixture_qdrant_env,
)
from tests.fixtures.golden_dataset import GoldenCase, load_golden_dataset
from tests.fixtures.malicious_prompts import load_malicious_prompts

_KNOWN_MALICIOUS_CATEGORIES = {
    "prompt_injection",
    "secret_exfiltration",
    "unregistered_tool",
}


def test_golden_dataset_ids_are_unique() -> None:
    cases = load_golden_dataset()
    ids = [case.id for case in cases]

    assert len(ids) == len(set(ids))
    assert len(cases) > 0


def test_golden_dataset_expected_sources_exist_in_fixture_knowledge_base() -> None:
    for case in load_golden_dataset():
        if not case.expect_grounded:
            continue
        assert case.expected_source is not None
        assert (FIXTURE_KNOWLEDGE_DIR / case.expected_source).is_file()


def test_malicious_prompt_ids_are_unique_with_known_categories() -> None:
    cases = load_malicious_prompts()
    ids = [case.id for case in cases]

    assert len(ids) == len(set(ids))
    assert len(cases) > 0
    for case in cases:
        assert case.category in _KNOWN_MALICIOUS_CATEGORIES


@pytest.mark.parametrize("case", load_golden_dataset(), ids=lambda case: case.id)
def test_fixture_query_knowledge_matches_golden_expectations(
    case: GoldenCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_fixture_qdrant_env(monkeypatch)

    result = fixture_query_knowledge(case.question)

    if not case.expect_grounded:
        assert result == NOT_FOUND_RESPONSE
        return
    assert case.expected_source in result
    for keyword in case.required_answer_keywords:
        assert keyword in result


def test_build_fixture_agent_runs_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    model = ScriptedToolCallingChatModel(
        responses=[AIMessage(content="Fixture knowledge base is wired correctly.")]
    )
    agent = build_fixture_agent(monkeypatch, model)

    request = ChatRequest(
        message="How many dental check-ups does AfyaPlus cover?",
        thread_id="fixture-smoke-test",
    )
    response = run_chat(request, agent)

    assert response.response == "Fixture knowledge base is wired correctly."
