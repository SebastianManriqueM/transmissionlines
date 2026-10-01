"""Builders converting normalized catalog records into runtime models."""

import hashlib
import json
import warnings
from math import isfinite
from typing import Any

from transmissionlines.catalog.schemas import ConductorRecord, ConductorV2Record, GroundWireRecord, PhasePositionRecord, GroundWirePositionRecord
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import CatalogReference
from transmissionlines.models.configurations import CircuitConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.catalog.electrical_conversion import gmr_from_xl, req_from_xc, select_phase_resistance
from transmissionlines.calculations.cable import round_six_one_gmr, solid_round_wire_gmr
from transmissionlines.units import CableDiameter, CableGMR, ConductorWeight, Current, MaterialArea, RatedBreakingStrength, ResistancePerKft, TowerCoordinate


def _reference(record: Any, table: str, catalog_version: str) -> CatalogReference:
    return CatalogReference(catalog_version=catalog_version, table_name=table, record_id=record.record_id, source_id=record.source_id)


def conductor_gmr_resolution(record: ConductorV2Record | ConductorRecord) -> tuple[str, float | None]:
    """Identify the best catalog-backed or estimated phase GMR without warning."""
    if isinstance(record, ConductorV2Record) and record.gmr_ft is not None:
        return "published", float(record.gmr_ft)
    if record.internal_reactance_ohm_kft is not None:
        return "reactance-derived", gmr_from_xl(record.internal_reactance_ohm_kft)
    if record.diameter_inch is None:
        return "missing", None
    diameter = float(record.diameter_inch)
    if not isfinite(diameter) or diameter <= 0:
        raise ValueError(f"conductor {record.record_id!r}: diameter_inch must be finite and positive")
    if (isinstance(record, ConductorV2Record) and record.family in {"ACSR", "ACSR/AW", "ACSS"}
            and record.stranding == "6/1" and record.strand_diameter_al_in is not None
            and record.strand_diameter_core_in is not None and record.core_diameter_in is not None):
        estimate = round_six_one_gmr(
            diameter, aluminum_strand_in=float(record.strand_diameter_al_in),
            core_strand_in=float(record.strand_diameter_core_in),
            core_diameter_in=float(record.core_diameter_in),
        )
        if estimate is not None:
            return "strand-estimated", estimate
    return "radius-estimated", solid_round_wire_gmr(diameter)


def _conductor_gmr(
    record: ConductorV2Record | ConductorRecord, *, gmr_ft: float | None = None,
) -> CableGMR | None:
    if gmr_ft is not None and not isfinite(gmr_ft):
        raise ValueError("gmr_ft must be finite and positive")
    if gmr_ft is not None and gmr_ft <= 0:
        raise ValueError("gmr_ft must be finite and positive")
    method, value = conductor_gmr_resolution(record)
    if gmr_ft is not None and method in {"published", "reactance-derived"}:
        raise ValueError("catalog GMR already available; remove the gmr_ft override")
    if gmr_ft is not None:
        return CableGMR(gmr_ft, "foot")
    if value is None:
        return None
    if method == "strand-estimated":
        warnings.warn(
            f"conductor {record.record_id!r}: estimated GMR using equal current across aluminum and steel core strands; verify for engineering use",
            UserWarning, stacklevel=3,
        )
    elif method == "radius-estimated":
        warnings.warn(
            f"conductor {record.record_id!r} ({record.family}): estimated GMR using the solid-round-wire outer-radius approximation; verify for engineering use",
            UserWarning, stacklevel=3,
        )
    return CableGMR(value, "foot")


def conductor_from_record(
    record: ConductorV2Record | ConductorRecord, *, catalog_version: str,
    gmr_ft: float | None = None,
) -> ConductorSpec:
    """Convert a record to typed equipment with source-first backend GMR resolution.

    Parameters
    ----------
    record : ConductorV2Record or ConductorRecord
        Validated versioned conductor data.
    catalog_version : str
        Selected catalog version for the persistent reference.
    gmr_ft : float, optional
        Independently sourced cable GMR when the catalog lacks published GMR
        and internal reactance; overrides estimates but not catalog measurements.

    Returns
    -------
    ConductorSpec
        Selected conductor with resolved cable GMR when sufficient data exist.
    """
    if isinstance(record, ConductorV2Record):
        resistances = (record.ac_resistance_75c_ohm_kft, record.ac_resistance_50c_ohm_kft, record.ac_resistance_25c_ohm_kft)
        ampacity = record.ampacity_75c_a
        dc_resistance = record.dc_resistance_20c_ohm_kft
    else:
        resistances = (record.ac_resistance_75_ohm_kft, record.ac_resistance_50_ohm_kft, record.ac_resistance_25_ohm_kft)
        ampacity = record.ampacity_a
        dc_resistance = record.dc_resistance_ohm_kft
    resistance = select_phase_resistance(
        *(None if value is None else ResistancePerKft(float(value), "ohm / kilofoot") for value in resistances)
    ) if any(value is not None for value in resistances) else None
    values = BareConductorEquipment(
        conductor_diameter=None if record.diameter_inch is None else CableDiameter(record.diameter_inch, "inch"),
        conductor_gmr=_conductor_gmr(record, gmr_ft=gmr_ft),
        capacitance_radius=None if record.capacitance_reactance_mohm_kft is None else CableGMR(req_from_xc(record.capacitance_reactance_mohm_kft), "foot"),
        ampacity=None if ampacity is None else Current(float(ampacity), "ampere"),
        ac_resistance=resistance if resistance is not None else (None if isinstance(record, ConductorV2Record) or record.ac_resistance_ohm_kft is None else ResistancePerKft(record.ac_resistance_ohm_kft, "ohm / kilofoot")),
        dc_resistance=None if dc_resistance is None else ResistancePerKft(float(dc_resistance), "ohm / kilofoot"),
        weight=None if not isinstance(record, ConductorV2Record) or record.weight_lb_kft is None else ConductorWeight(float(record.weight_lb_kft), "pound_force / kilofoot"),
        rated_breaking_strength=None if not isinstance(record, ConductorV2Record) or record.rated_strength_lb is None else RatedBreakingStrength(float(record.rated_strength_lb), "pound_force"),
        total_material_area=None if not isinstance(record, ConductorV2Record) or record.total_area_in2 is None else MaterialArea(float(record.total_area_in2), "inch ** 2"),
    )
    name = f"{catalog_version}:conductor:{record.record_id}"
    if gmr_ft is not None:
        name += f":external-gmr-ft:{gmr_ft}"
    return ConductorSpec(name=name, equipment=values, catalog_reference=_reference(record, "conductors", catalog_version))


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


def phase_spec_from_record(record: ConductorV2Record | ConductorRecord, *, circuit_id: str, insulator_string: InsulatorStringSpec | dict[str, Any], subconductor_count: int = 1, subconductor_spacing: Any = None, catalog_version: str) -> CircuitConfiguration:
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
