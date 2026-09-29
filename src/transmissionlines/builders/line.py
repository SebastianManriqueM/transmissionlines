"""Builders converting normalized catalog records into runtime models."""

import hashlib
import json
from typing import Any

from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord, PhasePositionRecord, GroundWirePositionRecord
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import CatalogReference
from transmissionlines.models.configurations import CircuitConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.catalog.electrical_conversion import gmr_from_xl, req_from_xc, select_phase_resistance
from transmissionlines.units import CableDiameter, CableGMR, Current, ResistancePerKft, TowerCoordinate


def _reference(record: Any, table: str, catalog_version: str) -> CatalogReference:
    return CatalogReference(catalog_version=catalog_version, table_name=table, record_id=record.record_id, source_id=record.source_id)


def conductor_from_record(record: ConductorRecord, *, catalog_version: str) -> ConductorSpec:
    """Convert one normalized phase-conductor record without retaining its row."""
    resistance = select_phase_resistance(
        None if record.ac_resistance_75_ohm_kft is None else ResistancePerKft(record.ac_resistance_75_ohm_kft, "ohm / kilofoot"),
        None if record.ac_resistance_50_ohm_kft is None else ResistancePerKft(record.ac_resistance_50_ohm_kft, "ohm / kilofoot"),
        None if record.ac_resistance_25_ohm_kft is None else ResistancePerKft(record.ac_resistance_25_ohm_kft, "ohm / kilofoot"),
    ) if any(value is not None for value in (record.ac_resistance_75_ohm_kft, record.ac_resistance_50_ohm_kft, record.ac_resistance_25_ohm_kft)) else None
    values = BareConductorEquipment(
        conductor_diameter=None if record.diameter_inch is None else CableDiameter(record.diameter_inch, "inch"),
        conductor_gmr=None if record.internal_reactance_ohm_kft is None else CableGMR(gmr_from_xl(record.internal_reactance_ohm_kft), "foot"),
        capacitance_radius=None if record.capacitance_reactance_mohm_kft is None else CableGMR(req_from_xc(record.capacitance_reactance_mohm_kft), "foot"),
        ampacity=None if record.ampacity_a is None else Current(record.ampacity_a, "ampere"),
        ac_resistance=resistance if resistance is not None else (None if record.ac_resistance_ohm_kft is None else ResistancePerKft(record.ac_resistance_ohm_kft, "ohm / kilofoot")),
        dc_resistance=None if record.dc_resistance_ohm_kft is None else ResistancePerKft(record.dc_resistance_ohm_kft, "ohm / kilofoot"),
    )
    return ConductorSpec(name=f"{catalog_version}:conductor:{record.record_id}", equipment=values, catalog_reference=_reference(record, "conductors", catalog_version))


def _circuit_configuration_name(
    conductor: ConductorSpec,
    circuit_id: str,
    bundle_spec: BundleSpec,
    insulator_string: InsulatorStringSpec,
) -> str:
    identity = {
        "conductor_name": conductor.name,
        "catalog_reference": (
            None if conductor.catalog_reference is None
            else conductor.catalog_reference.model_dump(mode="json")
        ),
        "equipment": conductor.equipment.model_dump(mode="json"),
        "circuit_id": circuit_id,
        "bundle_spec": bundle_spec.model_dump(mode="json"),
        "insulator_string": insulator_string.model_dump(mode="json"),
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{conductor.name}:{circuit_id}:{digest}"


def phase_spec_from_record(record: ConductorRecord, *, circuit_id: str, insulator_string: InsulatorStringSpec | dict[str, Any], subconductor_count: int = 1, subconductor_spacing: Any = None, catalog_version: str) -> CircuitConfiguration:
    """Build a registered circuit selection from one conductor record.

    Parameters
    ----------
    record : ConductorRecord
        Selected catalog conductor.
    circuit_id : str
        Circuit's geometry join key.
    insulator_string : InsulatorStringSpec or dict
        Required circuit installation input.
    subconductor_count : int
        Number of phase subconductors.
    subconductor_spacing : BundleSpacing, optional
        Spacing required for bundled phases.
    catalog_version : str
        Version of the selected catalog record.

    Returns
    -------
    CircuitConfiguration
        Independently registered circuit referencing a reusable conductor.
    """
    conductor = conductor_from_record(record, catalog_version=catalog_version)
    bundle_spec = BundleSpec(
        subconductor_count=subconductor_count,
        subconductor_spacing=subconductor_spacing,
    )
    insulator_spec = InsulatorStringSpec.model_validate(insulator_string)
    return CircuitConfiguration(
        name=_circuit_configuration_name(conductor, circuit_id, bundle_spec, insulator_spec),
        circuit_id=circuit_id,
        conductor_spec=conductor,
        bundle_spec=bundle_spec,
        insulator_string=insulator_spec,
    )


def ground_wire_from_record(record: GroundWireRecord, *, catalog_version: str) -> GroundWireSpec:
    """Build the shared unbundled ground-wire runtime specification."""
    conductor = BareConductorEquipment(
        conductor_diameter=None if record.diameter_inch is None else CableDiameter(record.diameter_inch, "inch"),
        dc_resistance=None if record.dc_resistance_ohm_kft is None else ResistancePerKft(record.dc_resistance_ohm_kft, "ohm / kilofoot"),
    )
    return GroundWireSpec(name=f"{catalog_version}:ground_wire:{record.record_id}", equipment=conductor, catalog_reference=_reference(record, "ground_wires", catalog_version))


def geometry_from_records(
    phase_records: list[PhasePositionRecord],
    ground_records: list[GroundWirePositionRecord],
    *,
    state_id: str | None = None,
) -> TowerGeometry:
    """Convert normalized position records into tower-local positions."""
    if state_id is not None:
        phase_records = [record for record in phase_records if record.state_id == state_id]
        ground_records = [record for record in ground_records if record.state_id == state_id]
    return TowerGeometry(
        phase_positions=[PhasePosition(circuit_id=r.circuit_id, phase=r.phase, x=TowerCoordinate(r.x, "foot"), y=TowerCoordinate(r.y, "foot")) for r in phase_records],
        ground_wire_positions=[GroundWirePosition(wire_id=r.wire_id, x=TowerCoordinate(r.x, "foot"), y=TowerCoordinate(r.y, "foot")) for r in ground_records],
    )


__all__ = ["conductor_from_record", "geometry_from_records", "ground_wire_from_record", "phase_spec_from_record"]
