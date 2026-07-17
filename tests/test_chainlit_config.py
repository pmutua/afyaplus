"""Tests for privacy-facing Chainlit configuration."""

import tomllib
from pathlib import Path

import pytest

from app.chainlit_app import _configure_cot_mode, chainlit_config

CHAINLIT_CONFIG = Path(__file__).parents[1] / ".chainlit" / "config.toml"


def test_hides_internal_steps_and_disables_uploads() -> None:
    with CHAINLIT_CONFIG.open("rb") as config_file:
        config = tomllib.load(config_file)

    assert config["UI"]["name"] == "AfyaPlus"
    assert config["UI"]["cot"] == "hidden"
    assert config["features"]["spontaneous_file_upload"]["enabled"] is False


def test_cot_mode_defaults_to_hidden_when_unset(monkeypatch) -> None:
    chainlit_config.ui.cot = "hidden"
    monkeypatch.delenv("CHAINLIT_COT_MODE", raising=False)

    _configure_cot_mode()

    assert chainlit_config.ui.cot == "hidden"


def test_env_var_overrides_cot_mode(monkeypatch) -> None:
    original_cot = chainlit_config.ui.cot
    monkeypatch.setenv("CHAINLIT_COT_MODE", "tool_call")
    try:
        _configure_cot_mode()
        assert chainlit_config.ui.cot == "tool_call"
    finally:
        chainlit_config.ui.cot = original_cot


def test_invalid_cot_mode_raises(monkeypatch) -> None:
    monkeypatch.setenv("CHAINLIT_COT_MODE", "verbose")

    with pytest.raises(ValueError, match="CHAINLIT_COT_MODE"):
        _configure_cot_mode()
