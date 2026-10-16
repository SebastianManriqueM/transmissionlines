"""Float field types that accept pint quantities at the model boundary.

Model fields store plain floats in the unit named by the field (``x_ft``,
``nominal_voltage_kv``). A field also accepts a pint quantity of the right
dimension, converted on the way in, so ``x_ft=Quantity(1, "meter")`` stores
3.28. Calculations only ever see the floats.
"""

from typing import Annotated, Any

import pint
from infrasys.base_quantity import ureg
from pydantic import BeforeValidator

Quantity = ureg.Quantity


def _in(unit: str) -> BeforeValidator:
    def convert(value: Any) -> Any:
        if not isinstance(value, pint.Quantity):
            return value
        try:
            return float(value.to(unit).magnitude)
        except pint.DimensionalityError as error:
            raise ValueError(f"expected a quantity convertible to {unit}, got {value.units}") from error
    return BeforeValidator(convert)


Amperes = Annotated[float, _in("ampere")]
Celsius = Annotated[float, _in("degC")]
Degrees = Annotated[float, _in("degree")]
Feet = Annotated[float, _in("foot")]
Hertz = Annotated[float, _in("hertz")]
Inches = Annotated[float, _in("inch")]
Kilovolts = Annotated[float, _in("kilovolt")]
Miles = Annotated[float, _in("mile")]
OhmMeters = Annotated[float, _in("ohm * meter")]
Ohms = Annotated[float, _in("ohm")]
OhmsPerKilofoot = Annotated[float, _in("ohm / kilofoot")]
PerKelvin = Annotated[float, _in("1 / kelvin")]
Pounds = Annotated[float, _in("pound_force")]
PoundsPerKilofoot = Annotated[float, _in("pound_force / kilofoot")]
Psi = Annotated[float, _in("psi")]
SquareInches = Annotated[float, _in("inch ** 2")]

__all__ = [
    "Amperes", "Celsius", "Degrees", "Feet", "Hertz", "Inches", "Kilovolts", "Miles",
    "OhmMeters", "Ohms", "OhmsPerKilofoot", "PerKelvin", "Pounds", "PoundsPerKilofoot",
    "Psi", "Quantity", "SquareInches",
]
