"""Immutable settings and external results for cross-section sag curves."""

import math
from uuid import UUID

from pydantic import ValidationInfo, field_validator, model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.result_base import CalculationResultModel
from transmissionlines.units import ElasticModulus, SpanLength, Temperature, ThermalExpansion


class SagOptions(LineDataModel):
    """Specify effective material properties and a hypothetical span grid.

    Parameters
    ----------
    elastic_modulus : ElasticModulus
        Effective modulus of one physical conductor; no catalog default exists.
    thermal_expansion_coefficient : ThermalExpansion
        Effective expansion per degree Celsius (equivalently per kelvin).
    reference_temperature, operating_temperature : Temperature
        Reference and operating conductor temperatures; defaults are 25 and 75 C.
    span_start, span_stop, span_step : SpanLength
        Horizontal span grid endpoints and step; defaults are 20, 2000 and 10 ft.
    elevation_difference : SpanLength
        Signed end-minus-start attachment rise; defaults to zero feet.
    additional_permanent_strain : float
        Additional dimensionless strain after the reference state.
    """

    elastic_modulus: ElasticModulus
    thermal_expansion_coefficient: ThermalExpansion
    reference_temperature: Temperature = Temperature(25, "degC")
    operating_temperature: Temperature = Temperature(75, "degC")
    additional_permanent_strain: float = 0.0
    span_start: SpanLength = SpanLength(20, "foot")
    span_stop: SpanLength = SpanLength(2000, "foot")
    span_step: SpanLength = SpanLength(10, "foot")
    elevation_difference: SpanLength = SpanLength(0, "foot")

    @field_validator(
        "elastic_modulus", "thermal_expansion_coefficient", "reference_temperature",
        "operating_temperature", "span_start", "span_stop", "span_step",
        "elevation_difference", mode="before",
    )
    @classmethod
    def require_explicit_units(cls, value: object, info: ValidationInfo) -> object:
        """Require the caller to specify a quantity with appropriate units."""
        expected = {
            "elastic_modulus": ElasticModulus,
            "thermal_expansion_coefficient": ThermalExpansion,
            "reference_temperature": Temperature,
            "operating_temperature": Temperature,
            "span_start": SpanLength,
            "span_stop": SpanLength,
            "span_step": SpanLength,
            "elevation_difference": SpanLength,
        }[info.field_name]
        if not isinstance(value, expected):
            raise ValueError(f"{info.field_name} requires an explicit {expected.__name__} quantity")
        return value

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
    span_lengths_ft: list[float]
    sag_ft: list[float]
    horizontal_tension_lb: list[float]

    @model_validator(mode="after")
    def validate_arrays(self) -> "SagCurve":
        """Ensure that every sampled span has one finite result."""
        if (not self.span_lengths_ft or len(self.span_lengths_ft) != len(self.sag_ft)
                or len(self.sag_ft) != len(self.horizontal_tension_lb)):
            raise ValueError("sag curve arrays must be nonempty and equal length")
        if (any(not math.isfinite(value) for array in (self.span_lengths_ft, self.sag_ft, self.horizontal_tension_lb) for value in array)
                or any(end <= start for start, end in zip(self.span_lengths_ft, self.span_lengths_ft[1:]))):
            raise ValueError("sag curve values must be finite with increasing spans")
        return self


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