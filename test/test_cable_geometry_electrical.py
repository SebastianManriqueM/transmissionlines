import numpy as np
import pytest

from transmissionlines.calculations.cable import bundle_gmr, ground_wire_gmr, regular_polygon_coordinates
from transmissionlines.calculations.geometry import direct_distance, image_distance
from transmissionlines.calculations.matrices import fully_transpose, kron_reduce, sequence_matrix
from transmissionlines.models.geometry import CablePosition
from transmissionlines.units import TowerCoordinate


def position(x: float, y: float) -> CablePosition:
    return CablePosition(x=TowerCoordinate(x, "foot"), y=TowerCoordinate(y, "foot"))


def test_direct_and_image_distances_use_tower_local_feet() -> None:
    first, second = position(0, 30), position(4, 40)
    assert direct_distance(first, second) == pytest.approx(np.sqrt(116))
    assert image_distance(first, second) == pytest.approx(np.sqrt(16 + 70**2))


def test_regular_polygon_and_bundle_gmr() -> None:
    coordinates = regular_polygon_coordinates(4, 12)
    assert np.allclose(np.linalg.norm(coordinates, axis=1), 12 / np.sqrt(2))
    assert bundle_gmr(0.1, 2, 12) == pytest.approx(np.sqrt(0.1))


def test_ground_wire_gmr_uses_overall_diameter() -> None:
    assert ground_wire_gmr(1.0) == pytest.approx(np.exp(-0.25) / 24)


def test_kron_and_sequence_dimensions() -> None:
    matrix = np.diag([1, 2, 3, 4]).astype(complex)
    reduced = kron_reduce(matrix, 3, 1)
    assert reduced.shape == (3, 3)
    transposed = fully_transpose(reduced)
    assert transposed.shape == (3, 3)
    assert sequence_matrix(transposed).shape == (3, 3)


def test_invalid_matrix_partition_fails_clearly() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        kron_reduce(np.eye(3), 3, 1)
