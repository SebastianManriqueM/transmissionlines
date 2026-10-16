"""Pure bundle geometry and derived cable-value calculations."""

from __future__ import annotations

from math import pi, sin
from typing import TYPE_CHECKING, Any

import numpy as np

from transmissionlines.units import CableGMR, EquivalentRadius

if TYPE_CHECKING:
    from transmissionlines.models.cables import BareConductorEquipment


def regular_polygon_coordinates(count: int, spacing: float | None) -> np.ndarray:
    """Return regular-polygon subconductor coordinates in inches.

    ``spacing`` is the adjacent subconductor spacing (the polygon side), and the
    first point is on the positive x axis.
    """
    if count == 1:
        return np.zeros((1, 2), dtype=float)
    radius = spacing / (2 * sin(pi / count))
    angles = 2 * pi * np.arange(count) / count
    return np.column_stack((radius * np.cos(angles), radius * np.sin(angles)))


def bundle_gmr(single_gmr: float, count: int, spacing: float | None) -> float:
    """Calculate complete-product bundle GMR in feet."""
    if count == 1:
        return single_gmr
    coords = regular_polygon_coordinates(count, spacing)
    coords /= 12.0
    product = 1.0
    for i in range(count):
        for j in range(count):
            distance = single_gmr if i == j else float(np.linalg.norm(coords[i] - coords[j]))
            product *= distance
    return product ** (1.0 / (count * count))


def equivalent_radius(radius: float, count: int, spacing: float | None) -> float:
    """Calculate the bundle's equivalent capacitance radius in feet."""
    if count == 1:
        return radius
    coords = regular_polygon_coordinates(count, spacing) / 12.0
    product = 1.0
    for i in range(count):
        for j in range(count):
            product *= radius if i == j else float(np.linalg.norm(coords[i] - coords[j]))
    return product ** (1.0 / (count * count))


def derived_bundle_values(
    conductor: BareConductorEquipment,
    count: int,
    spacing: Any,
) -> tuple[CableGMR | None, EquivalentRadius | None]:
    """Derive typed bundle values from a runtime conductor.

    ``capacitance_radius`` is parity-only catalog data derived from
    ``C_60Hz_Mohm_kft`` and takes precedence over physical diameter for the
    equivalent-radius calculation. It is intentionally optional at the model
    boundary because general runtime models may not have that catalog field.
    """
    spacing_value = None if spacing is None else spacing.to("inch").magnitude
    gmr = None if conductor.conductor_gmr is None else bundle_gmr(
        conductor.conductor_gmr.to("foot").magnitude, count, spacing_value
    )
    radius_source = conductor.capacitance_radius or conductor.conductor_diameter
    radius = None if radius_source is None else equivalent_radius(
        radius_source.to("foot").magnitude if conductor.capacitance_radius is not None else radius_source.to("foot").magnitude / 2,
        count,
        spacing_value,
    )
    return (None if gmr is None else CableGMR(gmr, "foot"),
            None if radius is None else EquivalentRadius(radius, "foot"))