"""JSON-safe electrical calculation result models."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from transmissionlines.models.result_base import CalculationResultModel


class MatrixResult(CalculationResultModel):
    """A named real/imaginary matrix with complete dimensional metadata."""

    name: str
    row_count: int
    column_count: int
    row_labels: list[str] = Field(default_factory=list)
    column_labels: list[str] = Field(default_factory=list)
    unit: str
    real: list[list[float]]
    imaginary: list[list[float]]

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


class ElectricalParameters(CalculationResultModel):
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
    circuit_scalars: dict[str, dict[str, float]] = Field(default_factory=dict)
    circuit_scalar_units: dict[str, dict[str, str]] = Field(default_factory=dict)
    circuit_ampacity_a: dict[str, float] = Field(default_factory=dict)
    circuit_subconductor_count: dict[str, int] = Field(default_factory=dict)
    provenance: list[Any] = Field(default_factory=list)
    calculated_at: datetime | None = None


__all__ = ["ElectricalParameters", "MatrixResult"]
