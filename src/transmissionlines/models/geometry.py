"""Tower-local geometry value models."""

from pydantic import model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.common import GroundWirePosition, PhasePosition


class TowerGeometry(LineDataModel):
    """Complete tower-local phase and ground-wire geometry."""

    phase_positions: list[PhasePosition]
    ground_wire_positions: list[GroundWirePosition]

    @model_validator(mode="after")
    def validate_geometry(self) -> "TowerGeometry":
        groups: dict[str, list[str]] = {}
        for position in self.phase_positions:
            groups.setdefault(position.circuit_id, []).append(position.phase)
        if not groups or any(sorted(phases) != ["A", "B", "C"] for phases in groups.values()):
            raise ValueError(
                "each configured circuit must have exactly A, B, and C phase positions"
            )
        if not self.ground_wire_positions:
            raise ValueError("at least one ground-wire position is required")
        return self


__all__ = ["TowerGeometry"]
