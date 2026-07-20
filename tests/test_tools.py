import math

import pytest

from app.agent.tools.calculator import calculate_medication_volume


def _calculate(dose_mg: float, concentration_mg_per_ml: float) -> str:
    return calculate_medication_volume.invoke(
        {
            "prescribed_dose_mg": dose_mg,
            "concentration_mg_per_ml": concentration_mg_per_ml,
        }
    )


def test_returns_medication_volume_for_valid_inputs() -> None:
    assert _calculate(250, 125) == "Medication volume: 2 mL."


@pytest.mark.parametrize("dose_mg", [0.0, -250.0])
def test_rejects_non_positive_prescribed_dose(dose_mg: float) -> None:
    result = _calculate(dose_mg, 125)

    assert result == (
        "Calculation error: prescribed_dose_mg must be greater than zero."
    )


def test_prevents_division_by_zero_when_concentration_is_zero() -> None:
    result = _calculate(250, 0)

    assert result == (
        "Calculation error: concentration_mg_per_ml must be greater than zero."
    )


def test_rejects_negative_concentration() -> None:
    result = _calculate(250, -125)

    assert result == (
        "Calculation error: concentration_mg_per_ml must be greater than zero."
    )


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_rejects_non_finite_inputs(value: float) -> None:
    result = _calculate(value, 125)

    assert result == "Calculation error: prescribed_dose_mg must be a finite number."
