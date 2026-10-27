from __future__ import annotations

import numpy as np
import pytest

from transmissionlines.calculations.cable import (
    bundle_gmr,
    derived_bundle_values,
    equivalent_radius,
    regular_polygon_coordinates,
    select_phase_resistance,
    strand_geometry_gmr,
)
from transmissionlines.calculations.electrical import build_primitive_p
from transmissionlines.calculations.geometry import image_distance
from transmissionlines.models.cables import BareConductorEquipment
from transmissionlines.models.geometry import PhasePosition
from transmissionlines.units import Distance, ResistancePerLength


def _conductor() -> BareConductorEquipment:
    return BareConductorEquipment(
        conductor_diameter=Distance(1, "inch"),
        conductor_gmr=Distance(0.04, "foot"),
        ac_resistance=ResistancePerLength(0.1, "ohm / kilofoot"),
        dc_resistance=ResistancePerLength(0.2, "ohm / kilofoot"),
    )


def test_bundle_formulas_cover_single_twin_and_multi_subconductors() -> None:
    assert regular_polygon_coordinates(1, None).tolist() == [[0.0, 0.0]]
    assert bundle_gmr(0.04, 1, None) == pytest.approx(0.04)
    assert bundle_gmr(0.04, 2, 12) == pytest.approx(np.sqrt(0.04))
    coordinates = regular_polygon_coordinates(3, 12)
    expected = np.prod(
        [
            [0.04 if i == j else np.linalg.norm((coordinates[i] - coordinates[j]) / 12) for j in range(3)]
            for i in range(3)
        ]
    ) ** (1 / 9)
    assert bundle_gmr(0.04, 3, 12) == pytest.approx(expected)


def test_strand_geometry_gmr_requires_explicit_round_strands_and_current_shares() -> None:
    single = strand_geometry_gmr([(0, 0)], [0.1], [1])
    assert single == pytest.approx(0.1 * np.exp(-0.25))
    two = strand_geometry_gmr([(0, 0), (0.2, 0)], [0.1, 0.1], [0.5, 0.5])
    assert two == pytest.approx(np.sqrt(0.1 * np.exp(-0.25) * 0.2))


def test_equivalent_radius_uses_same_polygon_policy() -> None:
    assert equivalent_radius(0.5 / 12, 1, None) == pytest.approx(0.5 / 12)
    assert equivalent_radius(0.5 / 12, 2, 12) == pytest.approx(np.sqrt((0.5 / 12) * 1.0))
    _, radius = derived_bundle_values(_conductor(), 2, Distance(1.0, "foot"))
    assert radius is not None
    assert radius.magnitude == pytest.approx(equivalent_radius(0.5 / 12, 2, 12))


def test_primitive_p_image_diagonal_and_matrix_metadata() -> None:
    positions = [
        PhasePosition(circuit_id="c1", phase="A", x=Distance(0, "foot"), y=Distance(30, "foot")),
        PhasePosition(circuit_id="c1", phase="B", x=Distance(4, "foot"), y=Distance(40, "foot")),
    ]
    result = build_primitive_p(positions, radii=[0.1, 0.1], frequency=60)
    assert result[0, 0] == pytest.approx(np.log(image_distance(positions[0], positions[0]) / 0.1) / (2 * np.pi * 1.4240e-2))
    assert result[0, 1] == pytest.approx(result[1, 0])


def test_resistance_policy_prefers_75_then_50_then_25() -> None:
    r25 = ResistancePerLength(0.25, "ohm / kilofoot")
    r50 = ResistancePerLength(0.50, "ohm / kilofoot")
    r75 = ResistancePerLength(0.75, "ohm / kilofoot")
    assert select_phase_resistance(r75, r50, r25) == r75
    assert select_phase_resistance(None, r50, r25) == r50
    assert select_phase_resistance(None, None, r25) == r25
    with pytest.raises(ValueError, match="requires"):
        select_phase_resistance()
