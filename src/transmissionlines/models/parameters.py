"""Aggregated line calculation parameters."""

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.mechanical import MechanicalParameters


class LineParameters(LineDataModel):
    """Independent electrical and mechanical calculation results."""

    electrical_parameters: ElectricalParameters | None = None
    mechanical_parameters: MechanicalParameters | None = None


__all__ = ["LineParameters"]
