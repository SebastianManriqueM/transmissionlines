"""Versioned catalog record schemas and source-header mappings."""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


# v1 (workbook) column names and their v2 equivalents. The workbook headers state
# these temperatures (R_20dc, R_25AC, ...); ac_resistance_ohm_kft duplicates R_75AC.
_V1_CONDUCTOR_COLUMNS = {
    "dc_resistance_ohm_kft": "dc_resistance_20c_ohm_kft",
    "ac_resistance_25_ohm_kft": "ac_resistance_25c_ohm_kft",
    "ac_resistance_50_ohm_kft": "ac_resistance_50c_ohm_kft",
    "ac_resistance_75_ohm_kft": "ac_resistance_75c_ohm_kft",
    "ac_resistance_ohm_kft": None,
}


class ConductorRecord(CatalogRecord):
    """One conductor row from either catalog version.

    v1 rows come from the Julia workbook and lack the PDF-backed fields; their
    legacy column names are mapped on load. ``ampacity_a`` and the reactances
    exist only in v1, whose ampacity rating conditions are unstated.
    """

    family: str
    codeword: str | None = None
    stranding: str | None = None
    size: str | None = None
    size_kcmil: float | None = None
    variant: str | None = None
    diameter_inch: float | None = None
    capacitance_reactance_mohm_kft: float | None = None
    internal_reactance_ohm_kft: float | None = None
    ampacity_a: float | None = None
    gmr_ft: Decimal | None = None
    weight_lb_kft: Decimal | None = None
    rated_strength_lb: Decimal | None = None
    aluminum_area_in2: Decimal | None = None
    core_area_in2: Decimal | None = None
    total_area_in2: Decimal | None = None
    core_diameter_in: Decimal | None = None
    strand_diameter_al_in: Decimal | None = None
    strand_diameter_core_in: Decimal | None = None
    ac_resistance_temperature_c: int | None = None
    ampacity_temperature_c: int | None = None
    dc_resistance_20c_ohm_kft: Decimal | None = None
    ac_resistance_25c_ohm_kft: Decimal | None = None
    ac_resistance_50c_ohm_kft: Decimal | None = None
    ac_resistance_75c_ohm_kft: Decimal | None = None
    ac_resistance_200c_ohm_kft: Decimal | None = None
    ampacity_75c_a: Decimal | None = None
    ampacity_100c_a: Decimal | None = None
    ampacity_150c_a: Decimal | None = None
    ampacity_180c_a: Decimal | None = None
    ampacity_200c_a: Decimal | None = None
    ampacity_250c_a: Decimal | None = None

    @model_validator(mode="before")
    @classmethod
    def _rename_v1_columns(cls, data: Any) -> Any:
        if isinstance(data, dict) and _V1_CONDUCTOR_COLUMNS.keys() & data.keys():
            data = dict(data)
            for old, new in _V1_CONDUCTOR_COLUMNS.items():
                value = data.pop(old, None)
                if new and value is not None:
                    data[new] = value
        return data


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
