"""Common immutable v3 value models."""

from typing import Literal

from infrasys import Component

from transmissionlines.models.base import LineDataModel
from transmissionlines.units import Angle, Distance, TowerCoordinate


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


class CablePosition(LineDataModel):
    """Tower-local cable position."""

    x: TowerCoordinate
    y: TowerCoordinate


class PhasePosition(CablePosition):
    """Position for one phase of one circuit."""

    circuit_id: str
    phase: Literal["A", "B", "C"]


class GroundWirePosition(CablePosition):
    """Position for one ground wire."""

    wire_id: str


__all__ = [
    "Bus",
    "CablePosition",
    "CatalogReference",
    "GeographicPoint",
    "GroundWirePosition",
    "IdentificationInfo",
    "PhasePosition",
]
