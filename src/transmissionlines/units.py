"""Quantity types for the transmission-line public model surface.

All quantities derive from :mod:`infrasys` ``BaseQuantity`` and therefore use the
same Pint unit registry that Infrasys uses for component and system serialization.
"""

from infrasys import BaseQuantity
from infrasys.quantities import Angle, Current, Distance, Resistance, Voltage


class TowerCoordinate(BaseQuantity):
    """Tower-local Cartesian coordinate using Julia-parity feet."""

    __base_unit__ = "foot"


class CableGMR(BaseQuantity):
    """Cable geometric mean radius using Julia-parity feet."""

    __base_unit__ = "foot"


class EquivalentRadius(BaseQuantity):
    """Equivalent conductor radius using Julia-parity feet."""

    __base_unit__ = "foot"


class BundleSpacing(BaseQuantity):
    """Subconductor bundle spacing using Julia-parity inches."""

    __base_unit__ = "inch"


class CableDiameter(BaseQuantity):
    """Cable diameter using Julia-parity inches."""

    __base_unit__ = "inch"


class RouteDistance(BaseQuantity):
    """Route or span length using mile-compatible distance units."""

    __base_unit__ = "mile"


class VoltageKV(BaseQuantity):
    """Nominal line voltage using kilovolts at persisted boundaries."""

    __base_unit__ = "kilovolt"


class Frequency(BaseQuantity):
    """Electrical frequency in hertz."""

    __base_unit__ = "hertz"


class EarthResistivity(BaseQuantity):
    """Earth resistivity in ohm-meter."""

    __base_unit__ = "ohm * meter"


class ResistancePerKft(BaseQuantity):
    """Cable resistance in ohms per kilofoot."""

    __base_unit__ = "ohm / kilofoot"


class SeriesImpedance(BaseQuantity):
    """Series impedance in ohms per mile."""

    __base_unit__ = "ohm / mile"


class ShuntAdmittance(BaseQuantity):
    """Shunt admittance in microsiemens per mile."""

    __base_unit__ = "microsiemens / mile"


class Temperature(BaseQuantity):
    """Temperature in kelvin."""

    __base_unit__ = "kelvin"


__all__ = [
    "Angle",
    "BaseQuantity",
    "BundleSpacing",
    "CableDiameter",
    "CableGMR",
    "Current",
    "Distance",
    "EarthResistivity",
    "EquivalentRadius",
    "Frequency",
    "Resistance",
    "ResistancePerKft",
    "RouteDistance",
    "SeriesImpedance",
    "ShuntAdmittance",
    "Temperature",
    "TowerCoordinate",
    "Voltage",
    "VoltageKV",
]
