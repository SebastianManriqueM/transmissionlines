"""Quantity types, one per physical dimension.

Infrasys supplies length (``Distance``), voltage, current, resistance, and angle;
this module defines only the dimensions it lacks. All share the Pint registry
Infrasys uses for serialization. Models reject bare numbers for quantity fields,
so ``Distance(3, "foot")``, never ``3``.
"""

from infrasys import BaseQuantity
from infrasys.quantities import Angle, Current, Distance, Resistance, Voltage


class Area(BaseQuantity):
    __base_unit__ = "inch ** 2"


class Force(BaseQuantity):
    __base_unit__ = "pound_force"


class ForcePerLength(BaseQuantity):
    __base_unit__ = "pound_force / kilofoot"


class Frequency(BaseQuantity):
    __base_unit__ = "hertz"


class InverseTemperature(BaseQuantity):
    __base_unit__ = "1 / kelvin"


class Pressure(BaseQuantity):
    __base_unit__ = "psi"


class ResistancePerLength(BaseQuantity):
    __base_unit__ = "ohm / kilofoot"


class Resistivity(BaseQuantity):
    __base_unit__ = "ohm * meter"


class Temperature(BaseQuantity):
    __base_unit__ = "kelvin"


__all__ = [
    "Angle",
    "Area",
    "BaseQuantity",
    "Current",
    "Distance",
    "Force",
    "ForcePerLength",
    "Frequency",
    "InverseTemperature",
    "Pressure",
    "Resistance",
    "ResistancePerLength",
    "Resistivity",
    "Temperature",
    "Voltage",
]
