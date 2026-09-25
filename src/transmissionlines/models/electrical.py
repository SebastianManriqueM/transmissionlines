"""Immutable electrical calculation result schemas."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from transmissionlines.models.base import LineDataModel


class MatrixResult(LineDataModel):
    name: str
    row_count: int = Field(gt=0)
    column_count: int = Field(gt=0)
    row_labels: list[str] = []
    column_labels: list[str] = []
    unit: str
    real: list[list[float]]
    imaginary: list[list[float]]


class ElectricalParameters(LineDataModel):
    method: str = "julia-parity"
    version: str = "1"
    status: Literal["incomplete", "complete"] = "incomplete"
    topology: Literal["one-circuit", "two-circuit"] | None = None
    units: dict[str, str] = {"z": "ohm/mile", "y": "microsiemens/mile"}
    labels: list[str] = []
    matrices: dict[str, MatrixResult] = {}
    scalars: dict[str, float] = {}
    scalar_units: dict[str, str] = {}
    provenance: list[dict[str, str | None]] = []
    calculated_at: datetime | None = None


__all__ = ["ElectricalParameters", "MatrixResult"]
