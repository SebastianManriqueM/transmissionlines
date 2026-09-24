"""Pure tower-local geometry calculations in legacy feet."""

from math import hypot

import numpy as np

from transmissionlines.models.geometry import CablePosition


def direct_distance(first: CablePosition, second: CablePosition) -> float:
    """Return the direct distance between two cable positions in feet."""
    dx = first.x.to("foot").magnitude - second.x.to("foot").magnitude
    dy = first.y.to("foot").magnitude - second.y.to("foot").magnitude
    return hypot(dx, dy)


def image_distance(first: CablePosition, second: CablePosition) -> float:
    """Return distance to the image of ``second`` below ground, in feet."""
    dx = first.x.to("foot").magnitude - second.x.to("foot").magnitude
    y1 = first.y.to("foot").magnitude
    y2 = second.y.to("foot").magnitude
    return hypot(dx, y1 + y2)


def pairwise_distances(positions: list[CablePosition]) -> np.ndarray:
    """Return a symmetric matrix of direct distances in feet."""
    if not positions:
        raise ValueError("positions cannot be empty")
    n = len(positions)
    result = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i):
            result[i, j] = result[j, i] = direct_distance(positions[i], positions[j])
    return result


def pairwise_image_distances(positions: list[CablePosition]) -> np.ndarray:
    """Return a matrix of image distances in feet."""
    if not positions:
        raise ValueError("positions cannot be empty")
    return np.array([[image_distance(a, b) for b in positions] for a in positions], dtype=float)


# Julia-compatible names retained for callers porting the old API.
get_distance_xy = direct_distance
get_all_distances = pairwise_distances

__all__ = ["direct_distance", "get_all_distances", "get_distance_xy", "image_distance", "pairwise_distances", "pairwise_image_distances"]
