"""Canonical route component exports."""

from transmissionlines.models.core import ElectricalTower, LineSpan

Tower = ElectricalTower

__all__ = ["LineSpan", "Tower"]
