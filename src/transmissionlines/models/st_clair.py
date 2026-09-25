"""Compact immutable models for St. Clair loadability calculations."""

from pydantic import Field, model_validator
from datetime import UTC, datetime

from transmissionlines.models.base import LineDataModel


class StClairOptions(LineDataModel):
    """Validated St. Clair operating limits and search resolutions."""

    abs_e1_pu: float = 1.0
    abs_e2_pu: float = 1.0
    r_system_1_ohm: float = 0.1
    x_system_1_ohm: float = 1.0
    r_system_2_ohm: float = 0.1
    x_system_2_ohm: float = 1.0
    n_s_percent: float = 0.0
    n_r_percent: float = 0.0
    n_series_percent: float = 0.0
    receiving_voltage_limit_pu: float = 0.95
    stability_angle_limit_deg: float = 45.0
    angle_step_deg: float = 0.5
    line_length_start_mi: float = 20.0
    line_length_stop_mi: float = 600.0
    line_length_step_mi: float = 1.0
    allow_near_zero_series_reactance: bool = False

    @model_validator(mode="after")
    def validate_options(self) -> "StClairOptions":
        if min(self.abs_e1_pu, self.abs_e2_pu, self.x_system_1_ohm, self.x_system_2_ohm) <= 0:
            raise ValueError("source voltage ratios and system reactances must be positive")
        if min(self.r_system_1_ohm, self.r_system_2_ohm) < 0:
            raise ValueError("system resistances cannot be negative")
        if not 0 < self.receiving_voltage_limit_pu <= 1.5:
            raise ValueError("receiving_voltage_limit_pu must be in (0, 1.5]")
        if not 0 < self.stability_angle_limit_deg <= 180 or self.angle_step_deg <= 0:
            raise ValueError("angle limit must be in (0, 180] and angle step must be positive")
        if self.line_length_start_mi <= 0 or self.line_length_stop_mi < self.line_length_start_mi:
            raise ValueError("line lengths must be positive and stop must not precede start")
        if self.line_length_step_mi <= 0:
            raise ValueError("line_length_step_mi must be positive")
        if min(self.n_s_percent, self.n_r_percent, self.n_series_percent) < 0:
            raise ValueError("compensation percentages cannot be negative")
        if max(self.n_s_percent, self.n_r_percent, self.n_series_percent) >= 100:
            raise ValueError("compensation percentages must be less than 100")
        return self


class StClairLineConstants(LineDataModel):
    """Natural-unit positive-sequence constants and resolved terminal voltages."""

    circuit_id: str = "circuit-1"
    r_ohm_per_mile: float
    x_ohm_per_mile: float
    b_siemens_per_mile: float
    nominal_voltage_v: float
    e1_v: float
    e2_v: float
    conductor_ampacity_a: float
    subconductor_count: int = 1
    source_scalars: dict[str, str] = Field(
        default_factory=lambda: {"r": "r1", "x": "x1", "b": "b1"}
    )

    @model_validator(mode="after")
    def validate_constants(self) -> "StClairLineConstants":
        if min(
            self.r_ohm_per_mile,
            self.x_ohm_per_mile,
            self.b_siemens_per_mile,
            self.nominal_voltage_v,
            self.conductor_ampacity_a,
        ) <= 0:
            raise ValueError("line constants, voltage, and ampacity must be positive")
        if self.subconductor_count < 1:
            raise ValueError("subconductor_count must be positive")
        return self


class StClairCurve(LineDataModel):
    """One compact curve represented by parallel arrays, not point objects."""

    name: str = "base"
    circuit_id: str = "circuit-1"
    lengths_mi: list[float]
    pr_w: list[float]
    pr_mw: list[float]
    ps_w: list[float]
    ps_mw: list[float]
    loss_w: list[float]
    abs_es_volt: list[float]
    abs_er_volt: list[float]
    abs_er_pu: list[float]
    current_a: list[float]
    limiting_angle_deg: list[float]
    limit_type: list[str]
    es_real_volt: list[float]
    es_imag_volt: list[float]
    er_real_volt: list[float]
    er_imag_volt: list[float]
    i2_real_a: list[float]
    i2_imag_a: list[float]
    circuit_nominal_ampacity_a: float
    thermal_power_mw: float

    @model_validator(mode="after")
    def validate_parallel_arrays(self) -> "StClairCurve":
        arrays = (
            self.pr_w, self.pr_mw, self.ps_w, self.ps_mw, self.loss_w,
            self.abs_es_volt, self.abs_er_volt, self.abs_er_pu, self.current_a,
            self.limiting_angle_deg, self.limit_type, self.es_real_volt,
            self.es_imag_volt, self.er_real_volt, self.er_imag_volt,
            self.i2_real_a, self.i2_imag_a,
        )
        if any(len(array) != len(self.lengths_mi) for array in arrays):
            raise ValueError("St. Clair curve arrays must have equal lengths")
        return self


class StClairResult(LineDataModel):
    """Resolved options, constants, and compact base/sensitivity curves."""

    options: StClairOptions
    line_constants: list[StClairLineConstants]
    curves: list[StClairCurve]
    sensitivity_curves: list[StClairCurve] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    line_name: str | None = None
    units: dict[str, str] = Field(
        default_factory=lambda: {
            "voltage": "V line-to-line; stored terminal phasors are phase V",
            "impedance": "ohm",
            "series_per_mile": "ohm/mile",
            "susceptance_per_mile": "S/mile",
            "current": "A",
            "power": "W and MW",
            "length": "mile",
            "angle": "degree",
        }
    )
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    method: str = "three-mesh-positive-sequence"
    version: str = "1"


__all__ = ["StClairCurve", "StClairLineConstants", "StClairOptions", "StClairResult"]