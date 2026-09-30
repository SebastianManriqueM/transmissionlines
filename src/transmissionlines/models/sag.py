"""Immutable settings and external results for cross-section sag curves."""

import math
from uuid import UUID

from pydantic import ValidationInfo, field_validator, model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.result_base import CalculationResultModel
from transmissionlines.units import ElasticModulus, ThermalExpansion


class SagOptions(LineDataModel):
    """Specify effective material properties and a hypothetical span grid.

    Parameters
    ----------
    elastic_modulus : ElasticModulus
        Effective modulus of one physical conductor; no catalog default exists.
    thermal_expansion_coefficient : ThermalExpansion
        Effective expansion per degree Celsius (equivalently per kelvin).
    """

    elastic_modulus: ElasticModulus
    thermal_expansion_coefficient: ThermalExpansion
    reference_temperature_c: float = 25.0
    operating_temperature_c: float = 75.0
    additional_permanent_strain: float = 0.0
    span_start_ft: float = 20.0
    span_stop_ft: float = 2000.0
    span_step_ft: float = 10.0
    elevation_difference_ft: float = 0.0

    @field_validator("elastic_modulus", "thermal_expansion_coefficient", mode="before")
    @classmethod
    def require_explicit_units(cls, value: object, info: ValidationInfo) -> object:
        """Require the caller to specify a quantity with appropriate units."""
        expected = ElasticModulus if info.field_name == "elastic_modulus" else ThermalExpansion
        if not isinstance(value, expected):
            raise ValueError(f"{info.field_name} requires an explicit {expected.__name__} quantity")
        return value

    @model_validator(mode="after")
    def validate_sag_options(self) -> "SagOptions":
        """Reject non-finite and nonphysical material or span inputs."""
        values = (
            self.elastic_modulus.to("psi").magnitude,
            self.thermal_expansion_coefficient.to("1 / kelvin").magnitude,
            self.reference_temperature_c, self.operating_temperature_c,
            self.additional_permanent_strain, self.span_start_ft, self.span_stop_ft,
            self.span_step_ft, self.elevation_difference_ft,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("sag options must be finite")
        if values[0] <= 0:
            raise ValueError("elastic_modulus must be positive")
        if self.additional_permanent_strain < 0:
            raise ValueError("additional_permanent_strain must be nonnegative")
        if self.span_start_ft <= 0 or self.span_stop_ft < self.span_start_ft or self.span_step_ft <= 0:
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