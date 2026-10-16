"""Pure bundle geometry and derived cable-value calculations."""

from __future__ import annotations

from math import pi, sin
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from transmissionlines.models.cables import BareConductorEquipment


def regular_polygon_coordinates(count: int, spacing: float | None) -> np.ndarray:
    r"""Return regular-polygon subconductor coordinates in inches.

    ``spacing`` :math:`s` is the adjacent subconductor spacing (the polygon side),
    so the circumradius is :math:`R = s / (2 \sin(\pi/n))`. The first point is on
    the positive x axis.
    """
    if count == 1:
        return np.zeros((1, 2), dtype=float)
    radius = spacing / (2 * sin(pi / count))
    angles = 2 * pi * np.arange(count) / count
    return np.column_stack((radius * np.cos(angles), radius * np.sin(angles)))


def bundle_gmr(self_ft: float, count: int, spacing_in: float | None) -> float:
    r"""Geometric mean of all subconductor-pair distances in a regular bundle, in feet.

    .. math:: \mathrm{GMR}_{\text{bundle}} = \Big( \prod_{i=1}^{n} \prod_{j=1}^{n} d_{ij} \Big)^{1/n^2},
              \qquad d_{ii} = \text{self}

    The self term is the subconductor's GMR for series impedance, or its radius
    for the capacitance equivalent radius (``equivalent_radius``). Every row of a
    regular bundle is alike, so this equals the textbook
    :math:`(\text{self} \cdot d_{12} \cdots d_{1n})^{1/n}`; for two subconductors,
    :math:`\sqrt{\text{self} \cdot s}`.
    """
    if count == 1:
        return self_ft
    xy = regular_polygon_coordinates(count, spacing_in) / 12.0
    distances = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    np.fill_diagonal(distances, self_ft)
    return float(np.prod(distances) ** (1.0 / count**2))


# Same geometric mean, with the subconductor radius as the self term.
equivalent_radius = bundle_gmr


def derived_bundle_values(
    conductor: BareConductorEquipment,
    count: int,
    spacing_in: float | None,
) -> tuple[float | None, float | None]:
    """Derive bundle GMR and equivalent capacitance radius, both in feet.

    ``capacitance_radius`` is parity-only catalog data derived from
    ``C_60Hz_Mohm_kft`` and takes precedence over physical diameter for the
    equivalent-radius calculation. It is intentionally optional at the model
    boundary because general runtime models may not have that catalog field.
    """
    gmr = None if conductor.gmr_ft is None else bundle_gmr(conductor.gmr_ft, count, spacing_in)
    radius_ft = conductor.capacitance_radius_ft
    if radius_ft is None and conductor.diameter_in is not None:
        radius_ft = conductor.diameter_in / 24
    radius = None if radius_ft is None else equivalent_radius(radius_ft, count, spacing_in)
    return gmr, radius