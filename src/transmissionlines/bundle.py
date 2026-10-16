"""Pure bundle geometry and derived cable-value calculations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from transmissionlines.models.cables import BareConductorEquipment


def _polygon(count: int, spacing: float | None) -> np.ndarray:
    r"""Subconductor positions as complex numbers :math:`x + jy`.

    The n-th roots of unity :math:`\omega^k`, scaled so adjacent points are
    ``spacing`` :math:`s` apart: the circumradius is
    :math:`s / |1 - \omega| = s / (2 \sin(\pi/n))`. The first point is on the
    positive x axis.
    """
    if count == 1:
        return np.zeros(1, dtype=complex)
    roots = np.exp(2j * np.pi * np.arange(count) / count)
    return roots * spacing / abs(roots[1] - roots[0])


def regular_polygon_coordinates(count: int, spacing: float | None) -> np.ndarray:
    """Return regular-polygon subconductor (x, y) coordinates, in the units of ``spacing``.

    The complex positions of :func:`_polygon`, viewed as (real, imaginary) pairs.
    """
    return _polygon(count, spacing).view(np.float64).reshape(-1, 2)


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
    z = _polygon(count, spacing_in) / 12.0
    distances = np.abs(z[:, None] - z[None, :])
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