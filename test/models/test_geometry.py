import pytest

from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry


def test_tower_geometry_rejects_duplicate_and_incomplete_positions() -> None:
    with pytest.raises(ValueError, match="duplicate phase"):
        TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x_ft=0, y_ft=1)
                for phase in ("A", "B", "B")
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x_ft=0, y_ft=2)],
        )
    with pytest.raises(ValueError, match="exactly A, B, and C"):
        TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x_ft=0, y_ft=1)
                for phase in ("A", "B")
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x_ft=0, y_ft=2)],
        )
    with pytest.raises(ValueError, match="duplicate ground"):
        TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x_ft=0, y_ft=1)
                for phase in ("A", "B", "C")
            ],
            ground_wire_positions=[
                GroundWirePosition(wire_id="g1", x_ft=0, y_ft=2),
                GroundWirePosition(wire_id="g1", x_ft=1, y_ft=2),
            ],
        )
