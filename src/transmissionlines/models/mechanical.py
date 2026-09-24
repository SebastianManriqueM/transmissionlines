"""Mechanical calculation result value models."""

from transmissionlines.models.base import LineDataModel


class MechanicalParameters(LineDataModel):
    """Mechanical calculation result and its method metadata."""

    method: str
    version: str


__all__ = ["MechanicalParameters"]
