"""Optional complete line routing components."""

from math import asin, cos, radians, sin, sqrt

from infrasys import Component
from pydantic import computed_field, model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.common import GeographicPoint
from transmissionlines.units import RouteDistance

_EARTH_MILES = 3958.7613


def _horizontal(a: GeographicPoint, b: GeographicPoint) -> float:
    """Compute haversine distance in miles."""
    lat1, lat2 = (
        radians(a.latitude.to("degree").magnitude),
        radians(b.latitude.to("degree").magnitude),
    )
    dlat = lat2 - lat1
    dlon = radians(b.longitude.to("degree").magnitude - a.longitude.to("degree").magnitude)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_MILES * asin(sqrt(h))


class Tower(Component):
    """Registered tower on a route."""

    tower_id: str
    sequence: int
    location: GeographicPoint


class LineSpan(Component):
    """Registered consecutive route span."""

    span_id: str
    sequence: int
    from_tower: Tower
    to_tower: Tower

    @computed_field
    @property
    def span_length(self) -> RouteDistance:
        """Return endpoint-derived three-dimensional span length."""
        horizontal = _horizontal(self.from_tower.location, self.to_tower.location)
        a, b = self.from_tower.location.elevation, self.to_tower.location.elevation
        if a is None or b is None:
            return RouteDistance(horizontal, "mile")
        dz = (b.to("mile") - a.to("mile")).magnitude
        return RouteDistance(sqrt(horizontal * horizontal + dz * dz), "mile")

    @property
    def elevation_assumed_zero(self) -> bool:
        """Whether missing endpoint elevation was treated as zero."""
        return (
            self.from_tower.location.elevation is None or self.to_tower.location.elevation is None
        )


class RoutingInfo(LineDataModel):
    """Complete ordered route; towers and spans remain registered components."""

    towers: list[Tower]
    spans: list[LineSpan]

    @model_validator(mode="after")
    def validate_route(self) -> "RoutingInfo":
        if len(self.towers) < 2 or len(self.spans) != len(self.towers) - 1:
            raise ValueError("routing requires at least two towers and exactly N-1 spans")
        if len({t.tower_id for t in self.towers}) != len(self.towers) or len(
            {s.span_id for s in self.spans}
        ) != len(self.spans):
            raise ValueError("tower_id and span_id values must be unique")
        for i, span in enumerate(self.spans):
            if span.from_tower is not self.towers[i] or span.to_tower is not self.towers[i + 1]:
                raise ValueError("spans must reference consecutive towers")
        return self


__all__ = ["LineSpan", "RoutingInfo", "Tower"]
