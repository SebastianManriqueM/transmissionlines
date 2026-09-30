"""Versioned catalog record schemas and source-header mappings."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CatalogRecord(BaseModel):
    """Base normalized record; unknown source columns are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    source_id: str


class GeometryRecord(CatalogRecord):
    structure_code: str
    structure_type: str | None = None
    company: str | None = None
    state: str | None = None
    voltage_kv: float | None = None
    n_circuits: int | None = None
    n_ground_w: int | None = None


class GeometryStateRecord(CatalogRecord):
    geometry_id: str
    state_id: str


class PhasePositionRecord(CatalogRecord):
    geometry_id: str
    state_id: str | None = None
    circuit_id: str
    phase: str
    x: float
    y: float


class GroundWirePositionRecord(CatalogRecord):
    geometry_id: str
    state_id: str | None = None
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


class ConductorRecord(CatalogRecord):
    family: str
    codeword: str
    stranding: str | None = None
    size_kcmil: float | None = None
    diameter_inch: float | None = None
    ac_resistance_ohm_kft: float | None = None
    ac_resistance_25_ohm_kft: float | None = None
    ac_resistance_50_ohm_kft: float | None = None
    ac_resistance_75_ohm_kft: float | None = None
    dc_resistance_ohm_kft: float | None = None
    capacitance_reactance_mohm_kft: float | None = None
    internal_reactance_ohm_kft: float | None = None
    ampacity_a: float | None = None


class ConductorV2Record(ConductorRecord):
    """Represent a PDF-backed conductor without requiring absent measurements."""

    codeword: str | None = None
    size: str | None = None
    variant: str
    weight_lb_kft: Decimal | None = None
    rated_strength_lb: Decimal | None = None
    aluminum_area_in2: Decimal | None = None
    core_area_in2: Decimal | None = None
    total_area_in2: Decimal | None = None
    core_diameter_in: Decimal | None = None
    ac_resistance_temperature_c: int | None = None
    ampacity_temperature_c: int | None = None


class ConductorFieldProvenance(BaseModel):
    """Identify a PDF cell and calculation basis for one conductor field."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    field: str
    method: Literal["published", "cross_pdf", "derived", "assumed"]
    source_id: str
    row_key: str
    source_sha256: str
    page: int = Field(gt=0)
    source_field: str
    source_header: str | None = None
    raw_value: str | None = None
    unit: str | None = None
    input_fields: tuple[str, ...] = ()
    note: str = ""


class GroundWireRecord(CatalogRecord):
    family: str
    awg_or_stranding: str
    size_kcmil: float | None = None
    strand_diameter_inch: float | None = None
    diameter_inch: float | None = None
    dc_resistance_ohm_kft: float | None = None
    breaking_load_lb: float | None = None
    weight_lb_kft: float | None = None
    area_inches: float | None = None


class StateBorderRecord(CatalogRecord):
    state_code: str
    border_state_code: str


class ActualLineRecord(CatalogRecord):
    structure_code: str | None = None
    structure_type: str | None = None
    state_id: str | None = None
    miles: float | None = None
    voltage_kv: float | None = None


TABLE_MODELS: dict[str, type[CatalogRecord]] = {
    "tower_geometries": GeometryRecord,
    "geometry_states": GeometryStateRecord,
    "phase_positions": PhasePositionRecord,
    "ground_wire_positions": GroundWirePositionRecord,
    "states": StateRecord,
    "state_borders": StateBorderRecord,
    "sources": SourceRecord,
    "conductors": ConductorRecord,
    "ground_wires": GroundWireRecord,
    "actual_lines": ActualLineRecord,
}
SOURCE_HEADERS: dict[str, dict[str, str]] = {
    name: {field: field for field in model.model_fields} for name, model in TABLE_MODELS.items()
}

__all__ = [
    "ActualLineRecord",
    "CatalogRecord",
    "ConductorFieldProvenance",
    "ConductorRecord",
    "ConductorV2Record",
    "GeometryRecord",
    "GeometryStateRecord",
    "GroundWirePositionRecord",
    "GroundWireRecord",
    "PhasePositionRecord",
    "SOURCE_HEADERS",
    "SourceRecord",
    "StateBorderRecord",
    "StateRecord",
    "TABLE_MODELS",
]
