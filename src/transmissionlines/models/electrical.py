"""Serializable electrical calculation result models."""

from datetime import datetime
from typing import Any

from transmissionlines.models.base import LineDataModel


class ElectricalParameters(LineDataModel):
    """Julia-parity electrical matrices and scalar results.

    Complex matrices use ``{"real": ..., "imag": ...}`` cells so the model is
    JSON-safe without relying on NumPy's non-JSON complex representation.
    """

    method: str = "julia-parity"
    version: str = "1"
    status: str = "complete"
    units: dict[str, str] = {"z": "ohm/mile", "y": "microsiemens/mile"}
    labels: list[str] = []
    matrices: dict[str, list[list[dict[str, float]]]] = {}
    scalars: dict[str, float] = {}
    provenance: list[Any] = []
    calculated_at: datetime | None = None


__all__ = ["ElectricalParameters"]
