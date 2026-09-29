"""Physical support, endpoint, and per-span route inputs."""

from typing import Literal

from infrasys import Component
from pydantic import ConfigDict, model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.common import GeographicPoint
from transmissionlines.models.configurations import TowerConfiguration
def tower_component_name(line_name: str, sequence: int) -> str:
    """Return the canonical registered name for a tower."""
    return f"{line_name}:tower:{sequence:03d}"


def span_component_name(line_name: str, sequence: int) -> str:
    """Return the canonical registered name for a span."""
    return f"{line_name}:span:{sequence:03d}"


class RouteGeometry(LineDataModel):
    """Store ordered WGS84 coordinates for a single physical span."""

    coordinates: list[tuple[float, float]]
    source_feature_ids: list[str] = []

    @model_validator(mode="after")
    def validate_coordinates(self) -> "RouteGeometry":
        if len(self.coordinates) < 2 or any(
            not (-180 <= longitude <= 180 and -90 <= latitude <= 90)
            for longitude, latitude in self.coordinates
        ):
            raise ValueError("route_geometry requires at least two valid WGS84 coordinates")
        return self


class ElectricalTower(Component):
    """Represent an installed physical support and its selected configuration."""

    model_config = ConfigDict(extra="forbid")

    tower_id: str
    sequence: int
    location: GeographicPoint
    configuration: TowerConfiguration
    structure_form: Literal["pole", "lattice", "h_frame", "y_frame"]
    support_role: Literal["suspension", "retention", "terminal"]


class StartEnd(Component):
    """Bind the distinct installed supports of one physical span."""

    start: ElectricalTower
    end: ElectricalTower

    @model_validator(mode="after")
    def validate_endpoints(self) -> "StartEnd":
        if self.start.uuid == self.end.uuid:
            raise ValueError("span endpoint towers must differ")
        return self


class LineSpan(Component):
    """Registered consecutive route span."""

    span_id: str
    sequence: int
    start_end: StartEnd
    route_geometry: RouteGeometry

__all__ = ["ElectricalTower", "LineSpan", "RouteGeometry", "StartEnd", "span_component_name", "tower_component_name"]
