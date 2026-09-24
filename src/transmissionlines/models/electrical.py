"""JSON-safe electrical calculation result models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


class ElectricalParameters(LineDataModel):
    """Julia-parity matrices, scalar results, units, and provenance."""

    method: str = "julia-parity"
    version: str = "1"
    status: str = "complete"
    units: dict[str, str] = Field(
        default_factory=lambda: {"z": "ohm/mile", "y": "microsiemens/mile"}
    )
    labels: list[str] = Field(default_factory=list)
    matrices: dict[str, MatrixResult] = Field(default_factory=dict)
    scalars: dict[str, float] = Field(default_factory=dict)
    scalar_units: dict[str, str] = Field(default_factory=dict)
    provenance: list[Any] = Field(default_factory=list)
    calculated_at: datetime | None = None


__all__ = ["ElectricalParameters", "MatrixResult"]
