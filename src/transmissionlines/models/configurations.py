"""Reusable tower configurations."""

from infrasys import Component
from pydantic import model_validator

from transmissionlines.models.cables import GroundWireSpec, PhaseConductorSpec
from transmissionlines.models.geometry import TowerGeometry
from transmissionlines.models.common import IdentificationInfo


class TowerConfiguration(Component):
    """Reusable immutable tower engineering definition."""

    identification_info: IdentificationInfo
    geometry: TowerGeometry
    ground_wire_spec: GroundWireSpec
    phase_conductor_specs: list[PhaseConductorSpec]

    @model_validator(mode="after")
    def validate_specs(self) -> "TowerConfiguration":
        circuits = {p.circuit_id for p in self.geometry.phase_positions}
        selected = [p.circuit_id for p in self.phase_conductor_specs]
        if set(selected) != circuits or len(selected) != len(set(selected)):
            raise ValueError(
                "exactly one phase conductor specification is required per geometry circuit"
            )
        return self


__all__ = ["TowerConfiguration"]
