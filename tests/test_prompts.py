from app.agent.prompts import SYSTEM_PROMPT


def test_system_prompt_still_forbids_diagnosis_and_dosing() -> None:
    assert "diagnosing conditions" in SYSTEM_PROMPT
    assert "Never use the calculator to choose or validate a dose" in SYSTEM_PROMPT
