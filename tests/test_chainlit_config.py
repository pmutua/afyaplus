"""Tests for privacy-facing Chainlit configuration."""

import tomllib
from pathlib import Path

CHAINLIT_CONFIG = Path(__file__).parents[1] / ".chainlit" / "config.toml"


def test_hides_internal_steps_and_disables_uploads() -> None:
    with CHAINLIT_CONFIG.open("rb") as config_file:
        config = tomllib.load(config_file)

    assert config["UI"]["name"] == "AfyaPlus"
    assert config["UI"]["cot"] == "hidden"
    assert config["features"]["spontaneous_file_upload"]["enabled"] is False
