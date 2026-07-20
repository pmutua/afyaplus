"""Validated medication-volume calculation for the AfyaPlus agent."""

from __future__ import annotations

import math

from langchain_core.tools import tool


def _require_positive_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number.")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


@tool
def calculate_medication_volume(
    prescribed_dose_mg: float,
    concentration_mg_per_ml: float,
) -> str:
    """Calculate medication volume from a clinician-supplied dose and concentration.

    Use only when a qualified clinician has already supplied both the prescribed
    dose in milligrams and medication concentration in milligrams per millilitre.
    Do not use this tool to select a dose, prescribe medication, diagnose a
    condition, or decide whether a treatment is safe.
    """

    try:
        dose = _require_positive_finite(prescribed_dose_mg, "prescribed_dose_mg")
        concentration = _require_positive_finite(
            concentration_mg_per_ml,
            "concentration_mg_per_ml",
        )
        volume_ml = dose / concentration
        _require_positive_finite(volume_ml, "calculated volume")
    except (TypeError, ValueError, ZeroDivisionError) as error:
        return f"Calculation error: {error}"
    return f"Medication volume: {volume_ml:.6g} mL."
