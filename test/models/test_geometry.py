import pytest

from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.units import TowerCoordinate


def test_tower_geometry_rejects_duplicate_and_incomplete_positions() -> None:
    with pytest.raises(ValueError, match="duplicate phase"):
        TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x=TowerCoordinate(0, "foot"), y=TowerCoordinate(1, "foot"))
                for phase in ("A", "B", "B")
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"), y=TowerCoordinate(2, "foot"))],
        )
    with pytest.raises(ValueError, match="exactly A, B, and C"):
        TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x=TowerCoordinate(0, "foot"), y=TowerCoordinate(1, "foot"))
                for phase in ("A", "B")
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"), y=TowerCoordinate(2, "foot"))],
        )
    with pytest.raises(ValueError, match="duplicate ground"):
        TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x=TowerCoordinate(0, "foot"), y=TowerCoordinate(1, "foot"))
                for phase in ("A", "B", "C")
            ],
            ground_wire_positions=[
                GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"), y=TowerCoordinate(2, "foot")),
                GroundWirePosition(wire_id="g1", x=TowerCoordinate(1, "foot"), y=TowerCoordinate(2, "foot")),
            ],
        )
