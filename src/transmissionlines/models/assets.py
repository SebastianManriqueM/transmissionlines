"""Transmission-line static components and value models."""

from abc import ABC, abstractmethod

from infrasys import Component
from pydantic import ConfigDict, model_validator

from transmissionlines.models.common import Bus
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.routing import LineSpan
from transmissionlines.units import EarthResistivity, Frequency, VoltageKV


class AbstractTransmissionLine(Component, ABC):
    """Hold shared, positive electrical inputs for a transmission line."""

    model_config = ConfigDict(extra="forbid")

    nominal_voltage: VoltageKV
    nominal_frequency: Frequency
    earth_resistivity: EarthResistivity

    @abstractmethod
    def _line_variant(self) -> str:
        """Identify the concrete input variant."""

    @model_validator(mode="after")
    def validate_electrical_inputs(self) -> "AbstractTransmissionLine":
        if any(
            value.magnitude <= 0
            for value in (self.nominal_voltage, self.nominal_frequency, self.earth_resistivity)
        ):
            raise ValueError("nominal voltage, frequency, and earth resistivity must be positive")
        return self


class CrossSectionTransmissionLine(AbstractTransmissionLine):
    """Select a representative configuration without physical supports."""

    configuration: TowerConfiguration

    def _line_variant(self) -> str:
        return "cross-section"


class RoutedTransmissionLine(AbstractTransmissionLine):
    """Represent a physical route using only its ordered registered spans."""

    from_bus: Bus
    to_bus: Bus
    spans: list[LineSpan]

    def _line_variant(self) -> str:
        return "routed"

    @model_validator(mode="after")
    def validate_route(self) -> "RoutedTransmissionLine":
        if not self.spans:
            raise ValueError("routed line requires nonempty spans")
        if self.from_bus.uuid == self.to_bus.uuid:
            raise ValueError("from_bus and to_bus must be distinct")
        towers = [self.spans[0].start_end.start, *(span.start_end.end for span in self.spans)]
        if len({tower.uuid for tower in towers}) != len(towers):
            raise ValueError("ordered spans must have distinct supports")
        if len({tower.tower_id for tower in towers}) != len(towers):
            raise ValueError("tower_id values must be unique within a routed line")
        if len({span.span_id for span in self.spans}) != len(self.spans):
            raise ValueError("span_id values must be unique within a routed line")
        if towers[0].support_role != "terminal" or towers[-1].support_role != "terminal":
            raise ValueError("first and last supports must have terminal support_role")
        if towers[0].location != self.from_bus.location or towers[-1].location != self.to_bus.location:
            raise ValueError("terminal tower locations must match terminal bus locations")
        for index, span in enumerate(self.spans):
            start, end = span.start_end.start, span.start_end.end
            if span.sequence != index or start.sequence != index or end.sequence != index + 1:
                raise ValueError("spans and endpoint towers must be in sequence order")
            if index and self.spans[index - 1].start_end.end.uuid != start.uuid:
                raise ValueError("adjacent spans must share an endpoint tower")
            coordinates = span.route_geometry.coordinates
            for coordinate, tower in ((coordinates[0], start), (coordinates[-1], end)):
                longitude = tower.location.longitude.to("degree").magnitude
                latitude = tower.location.latitude.to("degree").magnitude
                if coordinate != (longitude, latitude):
                    raise ValueError("route_geometry endpoint must match its tower location")
        return self


__all__ = [
    "AbstractTransmissionLine",
    "CrossSectionTransmissionLine",
    "RoutedTransmissionLine",
]
