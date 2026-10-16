"""Tower-local conductor distances in feet."""

import numpy as np

from transmissionlines.models.geometry import CablePosition


def _xy(positions: list[CablePosition]) -> tuple[np.ndarray, np.ndarray]:
    return np.array([p.x_ft for p in positions]), np.array([p.y_ft for p in positions])


def pairwise_distances(positions: list[CablePosition]) -> np.ndarray:
    """Return the symmetric matrix of direct conductor-to-conductor distances in feet."""
    x, y = _xy(positions)
    return np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])


def pairwise_image_distances(positions: list[CablePosition]) -> np.ndarray:
    """Return distances from each conductor to every conductor's image below ground, in feet."""
    x, y = _xy(positions)
    return np.hypot(x[:, None] - x[None, :], y[:, None] + y[None, :])


__all__ = ["pairwise_distances", "pairwise_image_distances"]
