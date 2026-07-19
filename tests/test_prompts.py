from app.agent.prompts import SYSTEM_PROMPT


def test_system_prompt_instructs_focused_knowledge_queries() -> None:
    assert "search_afyaplus_knowledge" in SYSTEM_PROMPT
    assert "Strip member IDs" in SYSTEM_PROMPT
    assert "dilutes retrieval toward identity-verification content" in SYSTEM_PROMPT


def test_system_prompt_still_forbids_diagnosis_and_dosing() -> None:
    assert "diagnosing conditions" in SYSTEM_PROMPT
    assert "Never use the calculator to choose or validate a dose" in SYSTEM_PROMPT
