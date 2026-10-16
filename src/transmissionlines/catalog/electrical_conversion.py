"""Pure catalog-to-electrical measurement conversions."""

from math import exp

from transmissionlines.electrical_constants import (
    CAPACITIVE_REACTANCE_COEFFICIENT,
    KILOFEET_PER_MILE,
    SERIES_REACTANCE_COEFFICIENT,
)


def select_phase_resistance(
    resistance_75: float | None = None,
    resistance_50: float | None = None,
    resistance_25: float | None = None,
) -> float:
    """Select AC resistance at 75, then 50, then 25 degrees C."""
    for value in (resistance_75, resistance_50, resistance_25):
        if value is not None:
            return value
    raise ValueError("phase conductor requires an AC resistance at 75, 50, or 25 C")


def gmr_from_xl(xl: float, frequency: float = 60.0) -> float:
    r"""Convert catalog internal reactance (ohm/kilofoot) to GMR in feet.

    .. math:: \mathrm{GMR} = \exp\!\left( -\frac{5.28\, X_a}{L_C\, f} \right)
    """
    if xl <= 0 or frequency <= 0:
        raise ValueError("reactance and frequency must be positive")
    return exp(-(xl / (1 / KILOFEET_PER_MILE)) / (SERIES_REACTANCE_COEFFICIENT * frequency))


def req_from_xc(xc: float, frequency: float = 60.0) -> float:
    r"""Convert catalog capacitive reactance (MΩ·kilofoot) to equivalent radius in feet.

    The capacitive reactance at one-foot spacing is
    :math:`X'_a = \frac{1}{2\pi f}\frac{1}{2\pi\varepsilon} \ln\frac{1}{r} = \frac{1.779}{f} \ln\frac1r`
    MΩ·mile, so

    .. math:: r = \exp\!\left( -\frac{f\, X'_a / 5.28}{1.779} \right).
    """
    if xc <= 0 or frequency <= 0:
        raise ValueError("reactance and frequency must be positive")
    return exp(-(xc * frequency * (1 / KILOFEET_PER_MILE)) / CAPACITIVE_REACTANCE_COEFFICIENT)