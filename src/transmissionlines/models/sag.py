"""Immutable settings and external results for cross-section sag curves."""

import math
from uuid import UUID

from pydantic import model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.result_base import CalculationResultModel
from transmissionlines.units import Pressure, Distance, Temperature, InverseTemperature


class SagOptions(LineDataModel):
    """Specify effective material properties and a hypothetical span grid.

    Parameters
    ----------
    elastic_modulus : Pressure
        Effective modulus of one physical conductor; no catalog default exists.
    thermal_expansion_coefficient : InverseTemperature
        Effective expansion per degree Celsius (equivalently per kelvin).
    reference_temperature, operating_temperature : Temperature
        Reference and operating conductor temperatures; defaults are 25 and 75 C.
    span_start, span_stop, span_step : Distance
        Horizontal span grid endpoints and step; defaults are 20, 2000 and 10 ft.
    elevation_difference : Distance
        Signed end-minus-start attachment rise; defaults to zero feet.
    additional_permanent_strain : float
        Additional dimensionless strain after the reference state.
    """

    elastic_modulus: Pressure
    thermal_expansion_coefficient: InverseTemperature
    reference_temperature: Temperature = Temperature(25, "degC")
    operating_temperature: Temperature = Temperature(75, "degC")
    additional_permanent_strain: float = 0.0
    span_start: Distance = Distance(20, "foot")
    span_stop: Distance = Distance(2000, "foot")
    span_step: Distance = Distance(10, "foot")
    elevation_difference: Distance = Distance(0, "foot")

    @model_validator(mode="after")
    def validate_sag_options(self) -> "SagOptions":
        """Reject non-finite and nonphysical material or span inputs."""
        modulus_psi = self.elastic_modulus.to("psi").magnitude
        start_ft = self.span_start.to("foot").magnitude
        stop_ft = self.span_stop.to("foot").magnitude
        step_ft = self.span_step.to("foot").magnitude
        values = (
            modulus_psi,
            self.thermal_expansion_coefficient.to("1 / kelvin").magnitude,
            self.reference_temperature.to("kelvin").magnitude,
            self.operating_temperature.to("kelvin").magnitude,
            self.additional_permanent_strain,
            start_ft, stop_ft, step_ft, self.elevation_difference.to("foot").magnitude,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("sag options must be finite")
        if modulus_psi <= 0:
            raise ValueError("elastic_modulus must be positive")
        if self.additional_permanent_strain < 0:
            raise ValueError("additional_permanent_strain must be nonnegative")
        if start_ft <= 0 or stop_ft < start_ft or step_ft <= 0:
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