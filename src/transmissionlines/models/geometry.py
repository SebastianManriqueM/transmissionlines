"""Canonical immutable geometry value exports."""

from transmissionlines.models.core import GroundWirePosition, PhasePosition, TowerGeometry

CablePosition = PhasePosition

__all__ = ["CablePosition", "GroundWirePosition", "PhasePosition", "TowerGeometry"]
