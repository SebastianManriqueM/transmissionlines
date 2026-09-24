"""Versioned catalog record schemas and source-header mappings."""

from pydantic import BaseModel, ConfigDict


class CatalogRecord(BaseModel):
    """Base normalized record; unknown source columns are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    source_id: str


class GeometryRecord(CatalogRecord):
    structure_code: str
    structure_type: str | None = None


class GeometryStateRecord(CatalogRecord):
    geometry_id: str
    state_id: str


class PhasePositionRecord(CatalogRecord):
    geometry_id: str
    state_id: str
    circuit_id: str
    phase: str
    x: float
    y: float


class GroundWirePositionRecord(CatalogRecord):
    geometry_id: str
    state_id: str
    wire_id: str
    x: float
    y: float


class StateRecord(CatalogRecord):
    code: str
    usps_code: str | None = None
    canonical_name: str


class SourceRecord(CatalogRecord):
    citation: str
    sha256: str


TABLE_MODELS: dict[str, type[CatalogRecord]] = {
    "tower_geometries": GeometryRecord,
    "geometry_states": GeometryStateRecord,
    "phase_positions": PhasePositionRecord,
    "ground_wire_positions": GroundWirePositionRecord,
    "states": StateRecord,
    "sources": SourceRecord,
}
SOURCE_HEADERS: dict[str, dict[str, str]] = {
    name: {field: field for field in model.model_fields} for name, model in TABLE_MODELS.items()
}

__all__ = [
    "CatalogRecord",
    "GeometryRecord",
    "GeometryStateRecord",
    "GroundWirePositionRecord",
    "PhasePositionRecord",
    "SOURCE_HEADERS",
    "SourceRecord",
    "StateRecord",
    "TABLE_MODELS",
]
