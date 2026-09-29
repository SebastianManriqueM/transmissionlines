"""Common geographic and catalog input models."""

from infrasys import Component
from pydantic import model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.units import Angle, Distance
from transmissionlines.models.geometry import CablePosition, GroundWirePosition, PhasePosition


class GeographicPoint(LineDataModel):
    """Geographic location of a terminal or tower."""

    latitude: Angle
    longitude: Angle
    elevation: Distance | None = None

    @model_validator(mode="after")
    def validate_wgs84_coordinates(self) -> "GeographicPoint":
        """Reject latitude and longitude outside WGS84 degree bounds."""
        latitude = self.latitude.to("degree").magnitude
        longitude = self.longitude.to("degree").magnitude
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180 degrees")
        return self


class CatalogReference(LineDataModel):
    """Auditable pointer from runtime data to a catalog record."""

    catalog_version: str
    table_name: str
    record_id: str
    source_id: str | None = None


class IdentificationInfo(LineDataModel):
    """Optional source identification for an engineering configuration."""

    geometry_id: str | None = None
    structure_code: str | None = None


class Bus(Component):
    """Named network terminal."""

    location: GeographicPoint


__all__ = [
    "Bus",
    "CablePosition",
    "CatalogReference",
    "GeographicPoint",
    "GroundWirePosition",
    "IdentificationInfo",
    "PhasePosition",
]
