"""Common immutable v3 value models."""

from infrasys import Component

from transmissionlines.models.base import LineDataModel
from transmissionlines.units import Angle, Distance
from transmissionlines.models.geometry import CablePosition, GroundWirePosition, PhasePosition


class GeographicPoint(LineDataModel):
    """Geographic location of a terminal or tower."""

    latitude: Angle
    longitude: Angle
    elevation: Distance | None = None


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
    structure_type: str | None = None


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
