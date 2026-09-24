import numpy as np
import pytest

from transmissionlines.calculations.geometry import direct_distance, image_distance
from transmissionlines.models.geometry import CablePosition
from transmissionlines.units import TowerCoordinate


def position(x: float, y: float) -> CablePosition:
    return CablePosition(x=TowerCoordinate(x, "foot"), y=TowerCoordinate(y, "foot"))


def test_direct_and_image_distances_use_tower_local_feet() -> None:
    first, second = position(0, 30), position(4, 40)
    assert direct_distance(first, second) == pytest.approx(np.sqrt(116))
    assert image_distance(first, second) == pytest.approx(np.sqrt(16 + 70**2))
