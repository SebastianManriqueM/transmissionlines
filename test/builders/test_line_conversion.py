from math import exp

import pandas as pd
import pytest

from transmissionlines.builders.line import conductor_from_record, ground_wire_from_record, phase_spec_from_record
from transmissionlines.catalog.electrical_conversion import gmr_from_xl, req_from_xc
from transmissionlines.catalog.repository import CatalogRepository
from transmissionlines.catalog.schemas import ConductorRecord, ConductorV2Record, GroundWireRecord
from transmissionlines.electrical_constants import (
    CAPACITIVE_REACTANCE_COEFFICIENT,
    EPSILON_AIR,
    KILOFEET_PER_MILE,
    L_C,
    L_F,
    R_C,
    SERIES_REACTANCE_COEFFICIENT,
)
from transmissionlines.units import BundleSpacing


def test_v2_conductor_projects_mechanical_quantities() -> None:
    frame = pd.read_parquet("data/catalog/v2/conductors.parquet")
    row = frame.dropna(subset=["weight_lb_kft", "rated_strength_lb", "total_area_in2"]).iloc[0]
    selected = CatalogRepository("data/catalog/v2").select_exact("conductors", record_id=row.record_id)
    record = ConductorV2Record.model_validate(selected)

    spec = conductor_from_record(record, catalog_version="v2")

    assert spec.equipment.weight is not None
    assert spec.equipment.weight.to("pound_force / kilofoot").magnitude == pytest.approx(float(record.weight_lb_kft))
    assert spec.equipment.rated_breaking_strength is not None
    assert spec.equipment.rated_breaking_strength.to("pound_force").magnitude == pytest.approx(float(record.rated_strength_lb))
    assert spec.equipment.total_material_area is not None
    assert spec.equipment.total_material_area.to("inch ** 2").magnitude == pytest.approx(float(record.total_area_in2))
    assert spec.catalog_reference is not None
    assert spec.catalog_reference.catalog_version == "v2"
    phase = phase_spec_from_record(
        record, circuit_id="circuit-1", catalog_version="v2",
        insulator_string=dict(insulator_type="glass", number_of_insulators=12,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    assert phase.conductor_spec.equipment == spec.equipment
    assert phase.conductor_spec.catalog_reference == spec.catalog_reference


def test_v2_conductor_uses_explicit_electrical_temperature_columns() -> None:
    catalog = CatalogRepository("data/catalog/v2")
    for family in ("ACCC", "ACSS", "ACSS/TW"):
        row = catalog.table("conductors")
        record_id = row[row.family == family].iloc[0].record_id
        record = ConductorV2Record.model_validate(catalog.select_exact("conductors", record_id=record_id))
        equipment = conductor_from_record(record, catalog_version="v2").equipment

        resistance = next(
            (value for value in (record.ac_resistance_75c_ohm_kft, record.ac_resistance_50c_ohm_kft, record.ac_resistance_25c_ohm_kft) if value is not None),
            None,
        )
        assert equipment.ac_resistance is not None
        assert equipment.ac_resistance.magnitude == pytest.approx(float(resistance))
        assert equipment.dc_resistance is not None
        assert equipment.dc_resistance.magnitude == pytest.approx(float(record.dc_resistance_20c_ohm_kft))
        if record.ampacity_75c_a is None:
            assert equipment.ampacity is None
        else:
            assert equipment.ampacity is not None
            assert equipment.ampacity.magnitude == pytest.approx(float(record.ampacity_75c_a))


def test_v2_conductor_preserves_absent_mechanical_fields() -> None:
    record = ConductorV2Record(
        record_id="test", source_id="source", family="AAC", variant="standard",
        ac_resistance_ohm_kft=0.1, ac_resistance_200c_ohm_kft="0.2",
        ampacity_a=900, ampacity_200c_a="1100",
    )
    equipment = conductor_from_record(record, catalog_version="v2").equipment

    assert equipment.weight is None
    assert equipment.rated_breaking_strength is None
    assert equipment.total_material_area is None
    assert equipment.ac_resistance is None
    assert equipment.ampacity is None


def test_shared_electrical_constants_preserve_catalog_conversions() -> None:
    assert KILOFEET_PER_MILE == 5.28
    assert SERIES_REACTANCE_COEFFICIENT == 0.00202237
    assert CAPACITIVE_REACTANCE_COEFFICIENT == 1.779
    assert R_C == 0.00158836
    assert L_C == SERIES_REACTANCE_COEFFICIENT
    assert L_F == 7.6786
    assert EPSILON_AIR == 1.4240e-2
    assert gmr_from_xl(0.1) == exp(-(0.1 / (1 / 5.28)) / (0.00202237 * 60.0))
    assert req_from_xc(0.2) == exp(-(0.2 * 60.0 * (1 / 5.28)) / 1.779)


def test_catalog_records_convert_to_runtime_specs_with_provenance() -> None:
    conductors = pd.read_parquet("data/catalog/v1/conductors.parquet")
    wires = pd.read_parquet("data/catalog/v1/ground_wires.parquet")
    conductor = conductors[conductors.codeword == "Linnet_EX_K4_1"].iloc[0]
    wire = wires[(wires.family == "ACSR") & (wires.awg_or_stranding == "4/0 6/1")].iloc[0]
    selected = conductor_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        catalog_version="v1",
    )
    phase = phase_spec_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        circuit_id="circuit-1", catalog_version="v1",
        insulator_string=dict(insulator_type="glass", number_of_insulators=12,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    repeated_phase = phase_spec_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        circuit_id="circuit-1", catalog_version="v1",
        insulator_string=dict(insulator_type="glass", number_of_insulators=12,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    bundled_phase = phase_spec_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        circuit_id="circuit-1", catalog_version="v1", subconductor_count=2,
        subconductor_spacing=BundleSpacing(18, "inch"),
        insulator_string=dict(insulator_type="glass", number_of_insulators=12,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    alternate_insulator_phase = phase_spec_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        circuit_id="circuit-1", catalog_version="v1",
        insulator_string=dict(insulator_type="glass", number_of_insulators=10,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    alternate_circuit_phase = phase_spec_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        circuit_id="circuit-2", catalog_version="v1",
        insulator_string=dict(insulator_type="glass", number_of_insulators=12,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    other_conductor = conductors[conductors.record_id != conductor.record_id].iloc[0]
    alternate_conductor_phase = phase_spec_from_record(
        ConductorRecord.model_validate(other_conductor.to_dict()),
        circuit_id="circuit-1", catalog_version="v1",
        insulator_string=dict(insulator_type="glass", number_of_insulators=12,
                              insulator_code="U120B", insulator_coupling="ball_and_socket"),
    )
    ground = ground_wire_from_record(
        GroundWireRecord.model_validate(wire.to_dict()), catalog_version="v1"
    )
    assert selected.catalog_reference is not None
    assert selected.catalog_reference.table_name == "conductors"
    assert phase.conductor_spec.equipment == selected.equipment
    assert phase.bundle_spec.subconductor_count == 1
    assert phase.name == repeated_phase.name
    assert phase.name != bundled_phase.name
    assert phase.name != alternate_insulator_phase.name
    assert phase.name != alternate_circuit_phase.name
    assert phase.name != alternate_conductor_phase.name
    assert ground.catalog_reference is not None
    assert ground.catalog_reference.table_name == "ground_wires"
    assert selected.catalog_reference.catalog_version == ground.catalog_reference.catalog_version == "v1"
