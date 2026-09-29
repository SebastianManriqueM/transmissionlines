"""Pure cable and bundle derivations using the Julia parity contract."""

from math import exp, log

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


def ground_wire_gmr(diameter_inch: float) -> float:
    """Return ground-wire GMR in feet from its overall diameter in inches."""
    if diameter_inch <= 0:
        raise ValueError("diameter must be positive")
    return exp(-0.25) * (diameter_inch / 2.0) / 12.0


def xl_from_gmr(gmr: float, frequency: float = 60.0) -> float:
    """Convert GMR in feet to the Julia catalog internal reactance."""
    if gmr <= 0 or frequency <= 0:
        raise ValueError("GMR and frequency must be positive")
    return frequency * SERIES_REACTANCE_COEFFICIENT * log(1 / gmr) * (1 / KILOFEET_PER_MILE)


get_regpoly_xy_coord = regular_polygon_coordinates
get_gmr_bundling_xy = bundle_gmr
get_gmr_from_diameter_inch = ground_wire_gmr
get_gmr_from_XL = gmr_from_xl
get_XL_from_gmr = xl_from_gmr
get_req_from_XC = req_from_xc
select_phase_ac_resistance = select_phase_resistance

__all__ = ["bundle_gmr", "derived_bundle_values", "equivalent_radius", "get_gmr_bundling_xy", "get_gmr_from_XL", "get_gmr_from_diameter_inch", "get_req_from_XC", "get_regpoly_xy_coord", "get_XL_from_gmr", "ground_wire_gmr", "regular_polygon_coordinates", "select_phase_ac_resistance", "select_phase_resistance"]
