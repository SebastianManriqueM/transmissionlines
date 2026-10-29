"""Immutable settings and external results for cross-section sag curves."""

import math
from uuid import UUID

from pydantic import model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.result_base import CalculationResultModel
from transmissionlines.units import Celsius, Feet, PerKelvin, Psi


class SagOptions(LineDataModel):
    """Specify effective material properties and a hypothetical span grid.

    The modulus and expansion coefficient describe one physical conductor and have
    no catalog default. Spans form a horizontal grid; ``elevation_difference_ft`` is
    the signed end-minus-start attachment rise.
    """

    elastic_modulus_psi: Psi
    thermal_expansion_per_k: PerKelvin
    reference_temperature_c: Celsius = 25.0
    operating_temperature_c: Celsius = 75.0
    additional_permanent_strain: float = 0.0
    span_start_ft: Feet = 20.0
    span_stop_ft: Feet = 2000.0
    span_step_ft: Feet = 10.0
    elevation_difference_ft: Feet = 0.0

    @model_validator(mode="after")
    def validate_sag_options(self) -> "SagOptions":
        """Reject non-finite and nonphysical material or span inputs."""
        if not all(math.isfinite(getattr(self, field)) for field in type(self).model_fields):
            raise ValueError("sag options must be finite")
        if self.elastic_modulus_psi <= 0:
            raise ValueError("elastic_modulus_psi must be positive")
        if self.additional_permanent_strain < 0:
            raise ValueError("additional_permanent_strain must be nonnegative")
        if self.span_start_ft <= 0 or self.span_stop_ft < self.span_start_ft or self.span_step_ft <= 0:
            raise ValueError("span lengths and step must be positive and stop must not precede start")
        return self


class SagCurve(CalculationResultModel):
    """Store parallel span, maximum sag, and solved horizontal-tension arrays."""

    circuit_id: str
    conductor_uuid: UUID
    conductor_family: str | None = None
    conductor_codeword: str | None = None
    stranding: str | None = None
    rated_strength_lb: float | None = None
    weight_lb_kft: float | None = None
    span_lengths_ft: list[float]
    sag_ft: list[float]
    horizontal_tension_lb: list[float]


class SagCurveResult(CalculationResultModel):
    """Keep calculated curves separate from the registered input graph."""

    line_uuid: UUID
    line_name: str
    options: SagOptions
    everyday_tension_fraction: float
    used_default_everyday_tension: bool
    curves: list[SagCurve]
    warnings: list[str]
    method: str = "reference-length-catenary"
    version: str = "1"
    units: dict[str, str] = {"span": "ft", "sag": "ft", "horizontal_tension": "lbf"}