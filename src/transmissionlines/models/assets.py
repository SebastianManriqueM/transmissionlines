"""Transmission-line static components and value models."""

from infrasys import Component
from pydantic import model_validator

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from transmissionlines.system import TransmissionLineSystem

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.common import Bus
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.routing import RoutingInfo
from transmissionlines.units import EarthResistivity, Frequency, VoltageKV


class LineTechnicalInfo(LineDataModel):
    """Immutable electrical and terminal data for a line."""

    line_name: str
    nominal_voltage: VoltageKV
    nominal_frequency: Frequency
    earth_resistivity: EarthResistivity
    from_bus: Bus
    to_bus: Bus

    @model_validator(mode="after")
    def validate_values(self) -> "LineTechnicalInfo":
        if (
            self.nominal_voltage.magnitude <= 0
            or self.nominal_frequency.magnitude <= 0
            or self.earth_resistivity.magnitude <= 0
        ):
            raise ValueError("nominal voltage, frequency, and earth resistivity must be positive")
        if self.from_bus.name == self.to_bus.name:
            raise ValueError("from_bus and to_bus must be distinct")
        return self


class ElectricalParameters(LineDataModel):
    """Optional electrical result placeholder."""

    method: str
    version: str


class MechanicalParameters(LineDataModel):
    """Optional mechanical result placeholder."""

    method: str
    version: str


class LineParameters(LineDataModel):
    """Independent electrical and mechanical result container."""

    electrical_parameters: ElectricalParameters | None = None
    mechanical_parameters: MechanicalParameters | None = None


class TransmissionLine(Component):
    """Static transmission line component."""

    technical_info: LineTechnicalInfo
    tower_configuration: TowerConfiguration
    routing_info: RoutingInfo | None = None
    line_parameters: LineParameters | None = None

    def resolve_component_references(self, system: "TransmissionLineSystem") -> "TransmissionLine":
        """Replace nested bus copies with registered system components after load."""
        from transmissionlines.models.common import Bus

        from_bus = system.get_component(Bus, self.technical_info.from_bus.name)
        to_bus = system.get_component(Bus, self.technical_info.to_bus.name)
        info = self.technical_info.model_copy(update={"from_bus": from_bus, "to_bus": to_bus})
        return TransmissionLine.model_validate({**self.model_dump(), "technical_info": info})

    @model_validator(mode="after")
    def validate_line(self) -> "TransmissionLine":
        if self.name != self.technical_info.line_name:
            raise ValueError("TransmissionLine.name must equal technical_info.line_name")
        if self.routing_info is not None:
            first, last = self.routing_info.towers[0], self.routing_info.towers[-1]
            if (
                first.location != self.technical_info.from_bus.location
                or last.location != self.technical_info.to_bus.location
            ):
                raise ValueError("routing terminal towers must match terminal bus locations")
        return self


__all__ = [
    "ElectricalParameters",
    "LineParameters",
    "LineTechnicalInfo",
    "MechanicalParameters",
    "TransmissionLine",
]
