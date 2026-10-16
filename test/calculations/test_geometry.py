import numpy as np
import pytest

from transmissionlines.calculations.geometry import pairwise_distances, pairwise_image_distances
from transmissionlines.models.geometry import CablePosition


def position(x: float, y: float) -> CablePosition:
    return CablePosition(x_ft=x, y_ft=y)


def test_direct_and_image_distances_use_tower_local_feet() -> None:
    positions = [position(0, 30), position(4, 40)]
    direct, image = pairwise_distances(positions), pairwise_image_distances(positions)
    assert direct[0, 1] == direct[1, 0] == pytest.approx(np.sqrt(116))
    assert direct[0, 0] == 0
    assert image[0, 1] == image[1, 0] == pytest.approx(np.sqrt(16 + 70**2))
    assert image[0, 0] == pytest.approx(60)  # a conductor's own image is 2 * height away
