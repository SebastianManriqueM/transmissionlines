"""Reusable tower configurations."""

from infrasys import Component
from pydantic import model_validator

from transmissionlines.models.cables import BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.geometry import TowerGeometry
from transmissionlines.models.common import IdentificationInfo


class CircuitConfiguration(Component):
    """Select a reusable conductor and circuit-specific installation inputs."""

    circuit_id: str
    conductor_spec: ConductorSpec
    bundle_spec: BundleSpec
    insulator_string: InsulatorStringSpec


class TowerConfiguration(Component):
    """Reusable immutable tower engineering definition."""

    identification_info: IdentificationInfo
    geometry: TowerGeometry
    ground_wire_spec: GroundWireSpec
    circuits: list[CircuitConfiguration]

    @model_validator(mode="after")
    def validate_specs(self) -> "TowerConfiguration":
        circuits = {p.circuit_id for p in self.geometry.phase_positions}
        selected = [circuit.circuit_id for circuit in self.circuits]
        if set(selected) != circuits or len(selected) != len(set(selected)):
            raise ValueError(
                "exactly one circuit configuration is required per geometry circuit"
            )
        return self


__all__ = ["CircuitConfiguration", "TowerConfiguration"]
