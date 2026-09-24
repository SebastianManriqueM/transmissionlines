"""JSON-safe electrical calculation result models."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from transmissionlines.models.base import LineDataModel


class MatrixResult(LineDataModel):
    """A named real/imaginary matrix with complete dimensional metadata."""

    name: str
    row_count: int
    column_count: int
    row_labels: list[str] = Field(default_factory=list)
    column_labels: list[str] = Field(default_factory=list)
    unit: str
    real: list[list[float]]
    imaginary: list[list[float]]

    @model_validator(mode="after")
    def validate_shape(self) -> MatrixResult:
        if self.row_count < 1 or self.column_count < 1:
            raise ValueError("matrix dimensions must be positive")
        if len(self.real) != self.row_count or len(self.imaginary) != self.row_count:
            raise ValueError(f"{self.name} real and imaginary row counts do not match metadata")
        if any(len(row) != self.column_count for row in self.real + self.imaginary):
            raise ValueError(f"{self.name} values do not match metadata dimensions")
        if self.row_labels and len(self.row_labels) != self.row_count:
            raise ValueError(f"{self.name} row labels do not match row count")
        if self.column_labels and len(self.column_labels) != self.column_count:
            raise ValueError(f"{self.name} column labels do not match column count")
        return self

    @property
    def cells(self) -> list[list[dict[str, float]]]:
        """Return legacy-compatible JSON cells for readers of the first API."""
        return [
            [{"real": real, "imag": imag} for real, imag in zip(real_row, imag_row)]
            for real_row, imag_row in zip(self.real, self.imaginary)
        ]

    def __iter__(self) -> Iterator[list[dict[str, float]]]:  # type: ignore[override]
        """Iterate over legacy-compatible matrix rows."""
        return iter(self.cells)

    def __getitem__(self, index: int) -> list[dict[str, float]]:
        """Return one legacy-compatible matrix row."""
        return self.cells[index]


class ElectricalParameters(LineDataModel):
    """Julia-parity matrices, scalar results, units, and provenance.

    Canonical matrix keys retain the Julia names. The legacy aliases
    ``Z_kron``, ``Y_kron``, ``Z_transposed``, ``Y_transposed``,
    ``Z_sequence``, and ``Y_sequence`` are accepted as convenience lookups by
    the calculation service but are not part of the completeness requirement.
    """

    method: str = "julia-parity"
    version: str = "1"
    status: str = "incomplete"
    topology: Literal["one-circuit", "two-circuit"] | None = None
    units: dict[str, str] = Field(
        default_factory=lambda: {"z": "ohm/mile", "y": "microsiemens/mile"}
    )
    labels: list[str] = Field(default_factory=list)
    matrices: dict[str, MatrixResult] = Field(default_factory=dict)
    scalars: dict[str, float] = Field(default_factory=dict)
    scalar_units: dict[str, str] = Field(default_factory=dict)
    provenance: list[Any] = Field(default_factory=list)
    calculated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_completed_result(self) -> ElectricalParameters:
        if self.status != "complete":
            return self
        required = {
            "Zabcg", "Pabcg", "Z_kron_nt", "P_kron_nt", "Y_kron_nt",
            "Z012_nt", "Y012_nt", "Z_kron_ft", "Y_kron_ft", "Z012_ft", "Y012_ft",
        }
        missing = sorted(required - self.matrices.keys())
        if missing:
            raise ValueError(f"complete electrical result is missing matrices: {missing}")
        kron = self.matrices["Z_kron_nt"]
        if kron.row_count not in (3, 6) or kron.column_count != kron.row_count:
            raise ValueError("Z_kron_nt must be a 3 or 6 square phase matrix")
        topology = "one-circuit" if kron.row_count == 3 else "two-circuit"
        if self.topology is not None and self.topology != topology:
            raise ValueError(f"topology {self.topology!r} does not match matrix dimensions")
        expected_scalars = {"r0", "x0", "b0", "r1", "x1", "b1", "surge_impedance_ohm", "sil_mw"}
        if topology == "two-circuit":
            expected_scalars |= {"r0_mutual", "x0_mutual", "b0_mutual"}
        if missing_scalars := sorted(expected_scalars - self.scalars.keys()):
            raise ValueError(f"complete electrical result is missing scalars: {missing_scalars}")
        expected_units = {
            "r0": "ohm/mile", "x0": "ohm/mile", "r1": "ohm/mile", "x1": "ohm/mile",
            "b0": "microsiemens/mile", "b1": "microsiemens/mile",
            "surge_impedance_ohm": "ohm", "sil_mw": "MW",
        }
        if topology == "two-circuit":
            expected_units.update({"r0_mutual": "ohm/mile", "x0_mutual": "ohm/mile", "b0_mutual": "microsiemens/mile"})
        for key, unit in expected_units.items():
            if self.scalar_units.get(key) != unit:
                raise ValueError(f"scalar {key!r} must have unit {unit!r}")
        phase_labels = self.matrices["Z_kron_nt"].row_labels
        phase_size = 3 if topology == "one-circuit" else 6
        circuit_count = 1 if topology == "one-circuit" else 2
        sequence_labels = [
            f"{circuit}:{sequence}"
            for circuit in range(1, circuit_count + 1)
            for sequence in ("zero", "positive", "negative")
        ]
        if len(phase_labels) != phase_size or self.matrices["Z_kron_nt"].column_labels != phase_labels:
            raise ValueError("complete electrical result requires deterministic Kron matrix labels")
        for key in required:
            matrix = self.matrices[key]
            if matrix.name != key:
                raise ValueError(f"matrix key {key!r} does not match matrix name {matrix.name!r}")
            if not matrix.row_labels or not matrix.column_labels:
                raise ValueError(f"matrix {key!r} requires row and column labels")
        primitive = self.matrices["Zabcg"]
        if primitive.row_count != primitive.column_count or self.matrices["Pabcg"].row_count != primitive.row_count:
            raise ValueError("primitive matrices must have matching square dimensions")
        for key in ("Z_kron_nt", "P_kron_nt", "Y_kron_nt", "Z_kron_ft", "Y_kron_ft"):
            matrix = self.matrices[key]
            if (matrix.row_count, matrix.column_count) != (phase_size, phase_size):
                raise ValueError(f"{key} dimensions do not match topology")
            if matrix.row_labels != phase_labels or matrix.column_labels != phase_labels:
                raise ValueError(f"{key} labels do not match phase labels")
        for key in ("Z012_nt", "Y012_nt", "Z012_ft", "Y012_ft"):
            matrix = self.matrices[key]
            if (matrix.row_count, matrix.column_count) != (phase_size, phase_size):
                raise ValueError(f"{key} dimensions do not match topology")
            if matrix.row_labels != sequence_labels or matrix.column_labels != sequence_labels:
                raise ValueError(f"{key} labels do not match sequence labels")
        return self


__all__ = ["ElectricalParameters", "MatrixResult"]
