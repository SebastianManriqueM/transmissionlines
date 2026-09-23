"""Define semantic quantity types backed by the infrasys Pint registry."""
# mypy: disable-error-code=misc

from infrasys import BaseQuantity, quantities

ActivePower = quantities.ActivePower
Angle = quantities.Angle
Current = quantities.Current
Distance = quantities.Distance
Resistance = quantities.Resistance
Voltage = quantities.Voltage


class TowerCoordinate(BaseQuantity):
    """Represent a local tower coordinate in feet by default."""

    __base_unit__ = "foot"


class CableGMR(BaseQuantity):
    """Represent cable geometric mean radius in feet by default."""

    __base_unit__ = "foot"


class EquivalentRadius(BaseQuantity):
    """Represent an equivalent radius in feet by default."""

    __base_unit__ = "foot"


class BundleSpacing(BaseQuantity):
    """Represent bundle spacing in inches by default."""

    __base_unit__ = "inch"


class CableDiameter(BaseQuantity):
    """Represent cable diameter in inches by default."""

    __base_unit__ = "inch"


class RouteLength(BaseQuantity):
    """Represent route length in miles by default."""

    __base_unit__ = "mile"


class InsulatorLength(BaseQuantity):
    """Represent insulator length in feet by default."""

    __base_unit__ = "foot"


class InsulatorSpacing(BaseQuantity):
    """Represent insulator spacing in millimeters by default."""

    __base_unit__ = "millimeter"


class CreepDistancePerVoltage(BaseQuantity):
    """Represent creep distance per nominal voltage."""

    __base_unit__ = "millimeter / kilovolt"


class VoltageKV(BaseQuantity):
    """Represent nominal voltage in kilovolts by default."""

    __base_unit__ = "kilovolt"


class Frequency(BaseQuantity):
    """Represent electrical frequency in hertz by default."""

    __base_unit__ = "hertz"


class EarthResistivity(BaseQuantity):
    """Represent earth resistivity in ohm meters by default."""

    __base_unit__ = "ohm * meter"


class ResistancePerKft(BaseQuantity):
    """Represent resistance per thousand feet by default."""

    __base_unit__ = "ohm / kilofeet"


class ImpedancePerMile(BaseQuantity):
    """Represent impedance per mile by default."""

    __base_unit__ = "ohm / mile"


class ReactancePerKft(BaseQuantity):
    """Represent reactance per thousand feet by default."""

    __base_unit__ = "ohm / kilofeet"


class AdmittancePerMile(BaseQuantity):
    """Represent admittance per mile by default."""

    __base_unit__ = "microsiemens / mile"


class LegacyCapacitanceReactance(BaseQuantity):
    """Represent legacy capacitance reactance per thousand feet."""

    __base_unit__ = "megohm / kilofeet"


class ApparentPower(BaseQuantity):
    """Represent apparent power in megavolt amperes by default."""

    __base_unit__ = "megavolt_ampere"


class WeightPerLength(BaseQuantity):
    """Represent cable weight per thousand feet by default."""

    __base_unit__ = "pound / kilofeet"


class Force(BaseQuantity):
    """Represent force in pounds by default."""

    __base_unit__ = "pound"


class Area(BaseQuantity):
    """Represent area in square inches by default."""

    __base_unit__ = "inch ** 2"


class Temperature(BaseQuantity):
    """Represent temperature in kelvin by default."""

    __base_unit__ = "kelvin"


class Speed(BaseQuantity):
    """Represent speed in meters per second by default."""

    __base_unit__ = "meter / second"


class Pressure(BaseQuantity):
    """Represent pressure in pascals by default."""

    __base_unit__ = "pascal"


class Irradiance(BaseQuantity):
    """Represent irradiance in watts per square meter by default."""

    __base_unit__ = "watt / meter ** 2"


__all__ = [
    "ActivePower",
    "AdmittancePerMile",
    "Angle",
    "ApparentPower",
    "Area",
    "BaseQuantity",
    "BundleSpacing",
    "CableDiameter",
    "CableGMR",
    "CreepDistancePerVoltage",
    "Current",
    "Distance",
    "EarthResistivity",
    "EquivalentRadius",
    "Force",
    "Frequency",
    "ImpedancePerMile",
    "InsulatorLength",
    "InsulatorSpacing",
    "Irradiance",
    "LegacyCapacitanceReactance",
    "Pressure",
    "ReactancePerKft",
    "Resistance",
    "ResistancePerKft",
    "RouteLength",
    "Speed",
    "Temperature",
    "TowerCoordinate",
    "Voltage",
    "VoltageKV",
    "WeightPerLength",
    "quantities",
]