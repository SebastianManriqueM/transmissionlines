"""Immutable tower-local coordinate and cable-position models."""

from typing import Literal

from pydantic import model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.units import TowerCoordinate


class CablePosition(LineDataModel):
    """A cable coordinate relative to the tower centerline and ground."""

    x: TowerCoordinate
    y: TowerCoordinate


class PhasePosition(CablePosition):
    """Position of one phase in one circuit."""

    circuit_id: str
    phase: Literal["A", "B", "C"]


class GroundWirePosition(CablePosition):
    """Position of one unbundled ground wire."""

    wire_id: str


class TowerGeometry(LineDataModel):
    """Complete tower-local phase and ground-wire geometry."""

    phase_positions: list[PhasePosition]
    ground_wire_positions: list[GroundWirePosition]

    @model_validator(mode="after")
    def validate_geometry(self) -> "TowerGeometry":
        groups: dict[str, list[str]] = {}
        for position in self.phase_positions:
            groups.setdefault(position.circuit_id, []).append(position.phase)
        if len({(p.circuit_id, p.phase) for p in self.phase_positions}) != len(self.phase_positions):
            raise ValueError("duplicate phase positions are not allowed")
        if not groups or any(sorted(phases) != ["A", "B", "C"] for phases in groups.values()):
            raise ValueError("each configured circuit must have exactly A, B, and C phase positions")
        if not self.ground_wire_positions:
            raise ValueError("at least one ground-wire position is required")
        if len({p.wire_id for p in self.ground_wire_positions}) != len(self.ground_wire_positions):
            raise ValueError("duplicate ground-wire IDs are not allowed")
        return self


__all__ = ["CablePosition", "GroundWirePosition", "PhasePosition", "TowerGeometry"]
