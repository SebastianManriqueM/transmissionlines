"""Pure cable and bundle derivations using the Julia parity contract."""

from math import cos, exp, isclose, log, pi, sin

import numpy as np

from transmissionlines.bundle import (
    bundle_gmr,
    derived_bundle_values,
    equivalent_radius,
    regular_polygon_coordinates,
)
from transmissionlines.catalog.electrical_conversion import (
    gmr_from_xl,
    req_from_xc,
    select_phase_resistance,
)
from transmissionlines.electrical_constants import (
    KILOFEET_PER_MILE,
    SERIES_REACTANCE_COEFFICIENT,
)
from transmissionlines.calculations.constants import ROUND_STRAND_DIAMETER_REL_TOLERANCE


def ground_wire_gmr(diameter_inch: float) -> float:
    """Return ground-wire GMR in feet from its overall diameter in inches."""
    return solid_round_wire_gmr(diameter_inch)


def solid_round_wire_gmr(diameter_inch: float) -> float:
    """Estimate GMR in feet by treating the entire cable as a solid round wire."""
    return exp(-0.25) * (diameter_inch / 2.0) / 12.0


def round_six_one_gmr(
    diameter_inch: float, *, aluminum_strand_in: float,
    core_strand_in: float, core_diameter_in: float,
) -> float | None:
    """Estimate feet GMR for a verified round 6/1 layout with equal strand current.

    Return None when the supplied dimensions cannot support a concentric
    single-ring layout; the caller can then apply an explicit fallback policy.
    """
    measurements = (diameter_inch, aluminum_strand_in, core_strand_in, core_diameter_in)
    if not all(np.isfinite(value) and value > 0 for value in measurements):
        return None
    if not (isclose(core_diameter_in, core_strand_in, rel_tol=ROUND_STRAND_DIAMETER_REL_TOLERANCE)
            and isclose(diameter_inch, core_strand_in + 2 * aluminum_strand_in,
                        rel_tol=ROUND_STRAND_DIAMETER_REL_TOLERANCE)
            and isclose(aluminum_strand_in, core_strand_in,
                        rel_tol=ROUND_STRAND_DIAMETER_REL_TOLERANCE)):
        return None
    center_distance = (aluminum_strand_in + core_strand_in) / 2
    if center_distance < aluminum_strand_in:
        return None
    centers = [(0.0, 0.0)] + [
        (center_distance * cos(index * pi / 3), center_distance * sin(index * pi / 3))
        for index in range(6)
    ]
    radii = [core_strand_in / 2] + [aluminum_strand_in / 2] * 6
    return strand_geometry_gmr(centers, radii, [1 / 7] * 7) / 12


def strand_geometry_gmr(
    centers: list[tuple[float, float]], radii: list[float], weights: list[float],
) -> float:
    """Calculate cable GMR from validated round-strand geometry and current shares.

    Parameters
    ----------
    centers : list of tuple of float
        Strand center coordinates in a consistent length unit.
    radii : list of float
        Positive round-strand radii in the same unit.
    weights : list of float
        Nonnegative current fractions that sum to one; the caller must justify
        this distribution for the conductor and operating frequency.

    Returns
    -------
    float
        Single-cable GMR in the input length unit.
    """
    points = np.asarray(centers, dtype=float)
    radius = np.asarray(radii, dtype=float)
    share = np.asarray(weights, dtype=float)
    distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    np.fill_diagonal(distances, radius * exp(-0.25))
    return float(np.exp(np.sum(np.outer(share, share) * np.log(distances))))


def xl_from_gmr(gmr: float, frequency: float = 60.0) -> float:
    """Convert GMR in feet to the Julia catalog internal reactance."""
    return frequency * SERIES_REACTANCE_COEFFICIENT * log(1 / gmr) * (1 / KILOFEET_PER_MILE)


get_regpoly_xy_coord = regular_polygon_coordinates
get_gmr_bundling_xy = bundle_gmr
get_gmr_from_diameter_inch = ground_wire_gmr
get_gmr_from_XL = gmr_from_xl
get_XL_from_gmr = xl_from_gmr
get_req_from_XC = req_from_xc
select_phase_ac_resistance = select_phase_resistance

__all__ = ["bundle_gmr", "derived_bundle_values", "equivalent_radius", "get_gmr_bundling_xy", "get_gmr_from_XL", "get_gmr_from_diameter_inch", "get_req_from_XC", "get_regpoly_xy_coord", "get_XL_from_gmr", "ground_wire_gmr", "regular_polygon_coordinates", "select_phase_ac_resistance", "select_phase_resistance", "strand_geometry_gmr"]
