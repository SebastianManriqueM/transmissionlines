"""Electrical calculation result value models."""

from transmissionlines.models.base import LineDataModel


class ElectricalParameters(LineDataModel):
    """Electrical calculation result and its method metadata."""

    method: str
    version: str


__all__ = ["ElectricalParameters"]
