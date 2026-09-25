"""Pure cable and bundle derivations using the Julia parity contract."""

from math import exp, log

from transmissionlines.bundle import (
    bundle_gmr,
    derived_bundle_values,
    equivalent_radius,
    regular_polygon_coordinates,
)
from transmissionlines.units import ResistancePerKft


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


get_regpoly_xy_coord = regular_polygon_coordinates
get_gmr_bundling_xy = bundle_gmr
get_gmr_from_diameter_inch = ground_wire_gmr
get_gmr_from_XL = gmr_from_xl
get_XL_from_gmr = xl_from_gmr
get_req_from_XC = req_from_xc
select_phase_ac_resistance = select_phase_resistance

__all__ = ["bundle_gmr", "derived_bundle_values", "equivalent_radius", "get_gmr_bundling_xy", "get_gmr_from_XL", "get_gmr_from_diameter_inch", "get_req_from_XC", "get_regpoly_xy_coord", "get_XL_from_gmr", "ground_wire_gmr", "regular_polygon_coordinates", "select_phase_ac_resistance", "select_phase_resistance"]
