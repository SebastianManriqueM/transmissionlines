"""Builders for canonical component and value schemas."""

from typing import Any

from transmissionlines.calculations.cable import gmr_from_xl, req_from_xc, select_phase_resistance
from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord, GroundWirePositionRecord, PhasePositionRecord
from transmissionlines.models.cables import BareConductorEquipment, GroundWireSpec, PhaseConductorSpec
from transmissionlines.models.common import CatalogReference, ConductorMaterial
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.parameters import LineParameters
from transmissionlines.units import ResistancePerKft, TowerCoordinate


def _reference(record: Any, table: str, catalog_version: str) -> CatalogReference:
    """Create immutable catalog provenance from a normalized record."""
    return CatalogReference(
        catalog_version=catalog_version,
        table_name=table,
        record_id=record.record_id,
        source_id=record.source_id,
    )


def conductor_from_record(record: ConductorRecord, *, catalog_version: str) -> BareConductorEquipment:
    """Build immutable conductor measurement values from a catalog record."""
    resistance = select_phase_resistance(
        None if record.ac_resistance_75_ohm_kft is None else ResistancePerKft(record.ac_resistance_75_ohm_kft, "ohm / kilofoot"),
        None if record.ac_resistance_50_ohm_kft is None else ResistancePerKft(record.ac_resistance_50_ohm_kft, "ohm / kilofoot"),
        None if record.ac_resistance_25_ohm_kft is None else ResistancePerKft(record.ac_resistance_25_ohm_kft, "ohm / kilofoot"),
    ) if any(value is not None for value in (record.ac_resistance_75_ohm_kft, record.ac_resistance_50_ohm_kft, record.ac_resistance_25_ohm_kft)) else None
    return BareConductorEquipment(
        material=ConductorMaterial.OTHER,
        conductor_diameter=record.diameter_inch,
        conductor_gmr=None if record.internal_reactance_ohm_kft is None else gmr_from_xl(record.internal_reactance_ohm_kft),
        capacitance_radius=None if record.capacitance_reactance_mohm_kft is None else req_from_xc(record.capacitance_reactance_mohm_kft),
        ac_resistance=None if resistance is None else resistance.to("ohm / kilofoot").magnitude,
        dc_resistance=record.dc_resistance_ohm_kft,
    )


def phase_spec_from_record(
    record: ConductorRecord,
    *,
    circuit_id: str,
    subconductor_count: int = 1,
    subconductor_spacing: Any = None,
    catalog_version: str,
) -> PhaseConductorSpec:
    """Build a canonical phase-conductor component from a catalog record."""
    equipment = conductor_from_record(record, catalog_version=catalog_version)
    return PhaseConductorSpec(
        name=f"{circuit_id}:{record.record_id}",
        conductor=equipment,
        catalog_reference=_reference(record, "conductors", catalog_version),
        circuit_id=circuit_id,
        subconductor_count=subconductor_count,
        subconductor_spacing=subconductor_spacing,
    )


def ground_wire_from_record(record: GroundWireRecord, *, catalog_version: str) -> GroundWireSpec:
    """Build a canonical ground-wire component from a catalog record."""
    equipment = BareConductorEquipment(
        material=ConductorMaterial.OTHER,
        conductor_diameter=record.diameter_inch,
        dc_resistance=record.dc_resistance_ohm_kft,
    )
    return GroundWireSpec(
        name=record.record_id,
        conductor=equipment,
        catalog_reference=_reference(record, "ground_wires", catalog_version),
    )


def geometry_from_records(
    phase_records: list[PhasePositionRecord],
    ground_records: list[GroundWirePositionRecord],
    *,
    state_id: str | None = None,
) -> TowerGeometry:
    """Build an immutable tower geometry value from catalog records."""
    if state_id is not None:
        phase_records = [record for record in phase_records if record.state_id == state_id]
        ground_records = [record for record in ground_records if record.state_id == state_id]
    return TowerGeometry(
        phase_positions=[PhasePosition(circuit_id=record.circuit_id, phase=record.phase, x=TowerCoordinate(record.x, "foot"), y=TowerCoordinate(record.y, "foot")) for record in phase_records],
        ground_wire_positions=[GroundWirePosition(wire_id=record.wire_id, x=TowerCoordinate(record.x, "foot"), y=TowerCoordinate(record.y, "foot")) for record in ground_records],
    )


def replace_electrical_parameters(parameters: LineParameters, result: ElectricalParameters) -> LineParameters:
    """Return a line-parameter value with a replacement electrical result."""
    return parameters.model_copy(update={"electrical_parameters": result})


__all__ = ["conductor_from_record", "geometry_from_records", "ground_wire_from_record", "phase_spec_from_record", "replace_electrical_parameters"]
