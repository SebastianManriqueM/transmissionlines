import pandas as pd

from transmissionlines.builders.line import ground_wire_from_record, phase_spec_from_record
from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord


def test_catalog_records_convert_to_runtime_specs_with_provenance() -> None:
    conductors = pd.read_parquet("data/catalog/v1/conductors.parquet")
    wires = pd.read_parquet("data/catalog/v1/ground_wires.parquet")
    conductor = conductors[conductors.codeword == "Linnet_EX_K4_1"].iloc[0]
    wire = wires[(wires.family == "ACSR") & (wires.awg_or_stranding == "4/0 6/1")].iloc[0]
    phase = phase_spec_from_record(
        ConductorRecord.model_validate(conductor.to_dict()),
        circuit_id="circuit-1",
        catalog_version="v1",
    )
    ground = ground_wire_from_record(
        GroundWireRecord.model_validate(wire.to_dict()), catalog_version="v1"
    )
    assert phase.catalog_reference is not None
    assert phase.catalog_reference.table_name == "conductors"
    assert ground.catalog_reference is not None
    assert ground.catalog_reference.table_name == "ground_wires"
    assert phase.catalog_reference.catalog_version == ground.catalog_reference.catalog_version == "v1"
