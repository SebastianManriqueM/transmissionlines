"""Pure cable and bundle derivations using the Julia parity contract."""

from math import exp, log, pi, sin
from typing import Any

import numpy as np

from transmissionlines.models.cables import BareConductorEquipment
from transmissionlines.units import CableGMR, EquivalentRadius, ResistancePerKft


def regular_polygon_coordinates(count: int, spacing: float | None) -> np.ndarray:
    """Return regular-polygon subconductor coordinates in inches.

    ``spacing`` is the adjacent subconductor spacing (the polygon side), and the
    first point is on the positive x axis.
    """
    if count < 1:
        raise ValueError("subconductor count must be positive")
    if count == 1:
        if spacing is not None:
            raise ValueError("a single subconductor has no spacing")
        return np.zeros((1, 2), dtype=float)
    if spacing is None or spacing <= 0:
        raise ValueError("spacing must be positive")
    radius = spacing / (2 * sin(pi / count))
    angles = 2 * pi * np.arange(count) / count
    return np.column_stack((radius * np.cos(angles), radius * np.sin(angles)))


def bundle_gmr(single_gmr: float, count: int, spacing: float | None) -> float:
    """Calculate complete-product bundle GMR in feet."""
    if single_gmr <= 0:
        raise ValueError("single GMR must be positive")
    if count < 1:
        raise ValueError("subconductor count must be positive")
    if count == 1:
        if spacing is not None:
            raise ValueError("single subconductor spacing must be None")
        return single_gmr
    if spacing is None or spacing <= 0:
        raise ValueError("positive spacing is required for a bundle")
    coords = regular_polygon_coordinates(count, spacing)
    # Convert the inch polygon coordinates to feet before combining with GMR.
    coords /= 12.0
    product = 1.0
    for i in range(count):
        for j in range(count):
            distance = single_gmr if i == j else float(np.linalg.norm(coords[i] - coords[j]))
            product *= distance
    return product ** (1.0 / (count * count))


def equivalent_radius(radius: float, count: int, spacing: float | None) -> float:
    """Calculate the bundle's equivalent capacitance radius in feet."""
    if radius <= 0:
        raise ValueError("single conductor radius must be positive")
    if count == 1:
        if spacing is not None:
            raise ValueError("single subconductor spacing must be None")
        return radius
    if spacing is None or spacing <= 0:
        raise ValueError("positive spacing is required for a bundle")
    coords = regular_polygon_coordinates(count, spacing) / 12.0
    product = 1.0
    for i in range(count):
        for j in range(count):
            product *= radius if i == j else float(np.linalg.norm(coords[i] - coords[j]))
    return product ** (1.0 / (count * count))


def ground_wire_gmr(diameter_inch: float) -> float:
    """Return ground-wire GMR in feet from its overall diameter in inches."""
    if diameter_inch <= 0:
        raise ValueError("diameter must be positive")
    return exp(-0.25) * (diameter_inch / 2.0) / 12.0


def select_phase_resistance(
    resistance_75: ResistancePerKft | None = None,
    resistance_50: ResistancePerKft | None = None,
    resistance_25: ResistancePerKft | None = None,
) -> ResistancePerKft:
    """Select AC resistance at 75, then 50, then 25 degrees C."""
    for value in (resistance_75, resistance_50, resistance_25):
        if value is not None:
            return value
    raise ValueError("phase conductor requires an AC resistance at 75, 50, or 25 C")


def gmr_from_xl(xl: float, frequency: float = 60.0) -> float:
    """Convert catalog internal reactance to GMR in feet."""
    if xl <= 0 or frequency <= 0:
        raise ValueError("reactance and frequency must be positive")
    return exp(-(xl / (1 / 5.28)) / (0.00202237 * frequency))


def xl_from_gmr(gmr: float, frequency: float = 60.0) -> float:
    """Convert GMR in feet to the Julia catalog internal reactance."""
    if gmr <= 0 or frequency <= 0:
        raise ValueError("GMR and frequency must be positive")
    return frequency * 0.00202237 * log(1 / gmr) * (1 / 5.28)


def req_from_xc(xc: float, frequency: float = 60.0) -> float:
    """Convert catalog capacitive reactance to equivalent radius in feet."""
    if xc <= 0 or frequency <= 0:
        raise ValueError("reactance and frequency must be positive")
    return exp(-(xc * frequency * (1 / 5.28)) / 1.779)


def derived_bundle_values(
    conductor: BareConductorEquipment,
    count: int,
    spacing: Any,
) -> tuple[CableGMR | None, EquivalentRadius | None]:
    """Derive typed bundle values from a runtime conductor."""
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


get_regpoly_xy_coord = regular_polygon_coordinates
get_gmr_bundling_xy = bundle_gmr
get_gmr_from_diameter_inch = ground_wire_gmr
get_gmr_from_XL = gmr_from_xl
get_XL_from_gmr = xl_from_gmr
get_req_from_XC = req_from_xc
select_phase_ac_resistance = select_phase_resistance

__all__ = ["bundle_gmr", "derived_bundle_values", "equivalent_radius", "get_gmr_bundling_xy", "get_gmr_from_XL", "get_gmr_from_diameter_inch", "get_req_from_XC", "get_regpoly_xy_coord", "get_XL_from_gmr", "ground_wire_gmr", "regular_polygon_coordinates", "select_phase_ac_resistance", "select_phase_resistance"]
