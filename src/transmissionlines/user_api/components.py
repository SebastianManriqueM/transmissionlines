"""Resolve selected cable measurements and configure reusable towers."""

from collections.abc import Mapping, Sequence
from typing import Any

from transmissionlines.builders.line import (
    _circuit_configuration_name,
    conductor_from_record,
    geometry_from_records,
    ground_wire_from_record,
)
from transmissionlines.catalog.schemas import GroundWirePositionRecord, PhasePositionRecord
from transmissionlines.models.cables import BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.user_api.catalog import BrowsingCatalog


def select_conductor(
    catalog: BrowsingCatalog, *, record_id: str, gmr_ft: float | None = None,
) -> ConductorSpec:
    """Select a conductor, resolving cable GMR before bundle installation.

    Parameters
    ----------
    catalog : BrowsingCatalog
        Selected snapshot.
    record_id : str
        Exact conductor record ID.
    gmr_ft : float, optional
        Separately sourced single-cable GMR in feet, used only if absent in the catalog.

    Returns
    -------
    ConductorSpec
        Shared selected equipment with a resolved cable GMR.

    Raises
    ------
    ValueError
        When no valid GMR is available or the supplied measurement is invalid.
    """
    record = catalog.select("conductors", record_id)
    return conductor_from_record(record, catalog_version=catalog.catalog_version, gmr_ft=gmr_ft)


def select_ground_wire(catalog: BrowsingCatalog, *, record_id: str) -> GroundWireSpec:
    """Select a reusable, electrically complete catalog ground wire."""
    record = catalog.select("ground_wires", record_id)
    selected = ground_wire_from_record(record, catalog_version=catalog.catalog_version)
    if selected.equipment.conductor_diameter is None or selected.equipment.dc_resistance is None:
        raise ValueError(f"ground wire {record_id!r} needs diameter_inch and dc_resistance_ohm_kft")
    return selected


def configure_tower(
    catalog: BrowsingCatalog, *, geometry_id: str, name: str,
    ground_wire: GroundWireSpec, circuits: Sequence[Mapping[str, Any]],
) -> TowerConfiguration:
    """Join selected circuit equipment to validated tower-local geometry."""
    if not isinstance(ground_wire, GroundWireSpec):
        raise TypeError("ground_wire must be a selected GroundWireSpec")
    if ground_wire.equipment.conductor_diameter is None or ground_wire.equipment.dc_resistance is None:
        raise ValueError("ground_wire needs diameter and DC resistance")
    geometry = catalog.select("tower_geometries", geometry_id)
    circuit_ids = catalog.tower_circuits(geometry_id)
    phase_rows = catalog.positions("phase_positions", geometry_id)
    ground_rows = catalog.positions("ground_wire_positions", geometry_id)
    if not ground_rows or (geometry.n_ground_w is not None and len(ground_rows) != geometry.n_ground_w):
        raise ValueError("ground-wire position count disagrees with selected geometry")
    states = {row.get("state_id") for row in phase_rows + ground_rows}
    if len(states) != 1:
        raise ValueError("mixed position state tags or ambiguous geometry variants")
    phase = [PhasePositionRecord.model_validate(row) for row in phase_rows]
    ground = [GroundWirePositionRecord.model_validate(row) for row in ground_rows]
    selected_geometry = geometry_from_records(phase, ground)
    provided_ids = [entry["circuit_id"] for entry in circuits]
    if sorted(provided_ids) != list(circuit_ids):
        raise ValueError("circuits must select every geometry circuit exactly once")
    configurations = []
    for entry in circuits:
        conductor = entry["conductor"]
        bundle = entry["bundle"]
        if not isinstance(conductor, ConductorSpec) or not isinstance(bundle, BundleSpec):
            raise TypeError("each circuit needs a selected ConductorSpec and BundleSpec")
        insulator = InsulatorStringSpec.model_validate(entry["insulator"])
        circuit_id = entry["circuit_id"]
        configurations.append(CircuitConfiguration(
            name=_circuit_configuration_name(conductor, circuit_id, bundle, insulator),
            circuit_id=circuit_id, conductor_spec=conductor, bundle_spec=bundle,
            insulator_string=insulator,
        ))
    return TowerConfiguration(
        name=name, geometry=selected_geometry, ground_wire_spec=ground_wire,
        identification_info=IdentificationInfo(geometry_id=geometry_id, structure_code=geometry.structure_code),
        circuits=configurations,
    )