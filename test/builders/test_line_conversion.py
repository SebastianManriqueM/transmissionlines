from math import exp

import pandas as pd

from transmissionlines.builders.line import conductor_from_record, ground_wire_from_record, phase_spec_from_record
from transmissionlines.catalog.electrical_conversion import gmr_from_xl, req_from_xc
from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord
from transmissionlines.electrical_constants import (
    CAPACITIVE_REACTANCE_COEFFICIENT,
    EPSILON_AIR,
    KILOFEET_PER_MILE,
    L_C,
    L_F,
    R_C,
    SERIES_REACTANCE_COEFFICIENT,
)


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
    ground = ground_wire_from_record(
        GroundWireRecord.model_validate(wire.to_dict()), catalog_version="v1"
    )
    assert selected.catalog_reference is not None
    assert selected.catalog_reference.table_name == "conductors"
    assert phase.conductor_spec.equipment == selected.equipment
    assert phase.bundle_spec.subconductor_count == 1
    assert ground.catalog_reference is not None
    assert ground.catalog_reference.table_name == "ground_wires"
    assert selected.catalog_reference.catalog_version == ground.catalog_reference.catalog_version == "v1"
