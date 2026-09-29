"""Pure catalog-to-electrical measurement conversions."""

from math import exp

from transmissionlines.electrical_constants import (
    CAPACITIVE_REACTANCE_COEFFICIENT,
    KILOFEET_PER_MILE,
    SERIES_REACTANCE_COEFFICIENT,
)
from transmissionlines.units import ResistancePerKft


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
    return exp(-(xl / (1 / KILOFEET_PER_MILE)) / (SERIES_REACTANCE_COEFFICIENT * frequency))


def req_from_xc(xc: float, frequency: float = 60.0) -> float:
    """Convert catalog capacitive reactance to equivalent radius in feet."""
    if xc <= 0 or frequency <= 0:
        raise ValueError("reactance and frequency must be positive")
    return exp(-(xc * frequency * (1 / KILOFEET_PER_MILE)) / CAPACITIVE_REACTANCE_COEFFICIENT)