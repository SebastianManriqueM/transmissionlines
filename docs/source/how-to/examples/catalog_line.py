"""Build and calculate a two-circuit cross-section from the default v2 catalog."""

from transmissionlines.api import calculate_line_electrical_parameters, open_catalog
from transmissionlines.builders.line import (
    conductor_from_record,
    geometry_from_records,
    ground_wire_from_record,
)
from transmissionlines.catalog.schemas import (
    ConductorV2Record,
    GroundWirePositionRecord,
    GroundWireRecord,
    PhasePositionRecord,
)
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.cables import BundleSpec, ConductorSpec, InsulatorStringSpec
from transmissionlines.models.common import IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.units import CableGMR, EarthResistivity, Frequency, VoltageKV


def build_line():
    """Build the representative 3L11 line from exact catalog selections."""
    catalog = open_catalog()
    tower = catalog.select_exact("tower_geometries", structure_code="3L11")
    phase_rows = catalog.table("phase_positions")
    ground_rows = catalog.table("ground_wire_positions")
    phase_records = [
        PhasePositionRecord.model_validate(row)
        for row in phase_rows.loc[phase_rows.geometry_id == tower["record_id"]].to_dict("records")
    ]
    ground_records = [
        GroundWirePositionRecord.model_validate(row)
        for row in ground_rows.loc[ground_rows.geometry_id == tower["record_id"]].to_dict("records")
    ]
    geometry = geometry_from_records(phase_records, ground_records)

    conductor = ConductorV2Record.model_validate(
        catalog.select_exact("conductors", record_id="ACSR:954:cardinal:standard:54/7")
    )
    ground_wire = GroundWireRecord.model_validate(
        catalog.select_exact("ground_wires", record_id="Alumoweld:7/7:145.7:15")
    )
    insulator = InsulatorStringSpec(
        insulator_type="glass",
        number_of_insulators=12,
        insulator_code="U120B",
        insulator_coupling="ball_and_socket",
    )
    selected = conductor_from_record(conductor, catalog_version=catalog.catalog_version)
    phase_equipment = selected.equipment.model_copy(update={
        "conductor_gmr": CableGMR(0.04, "foot"),
        "capacitance_radius": CableGMR(0.0498, "foot"),
    })
    phase_conductor = ConductorSpec(
        name=selected.name, equipment=phase_equipment,
        catalog_reference=selected.catalog_reference,
    )
    circuits = [
        CircuitConfiguration(
            name=f"3L11:{circuit_id}:cardinal",
            circuit_id=circuit_id,
            conductor_spec=phase_conductor,
            bundle_spec=BundleSpec(subconductor_count=1),
            insulator_string=insulator,
        )
        for circuit_id in sorted({position.circuit_id for position in geometry.phase_positions})
    ]
    configuration = TowerConfiguration(
        name="3L11-cardinal",
        identification_info=IdentificationInfo(
            geometry_id=tower["record_id"], structure_code=tower["structure_code"]
        ),
        geometry=geometry,
        circuits=circuits,
        ground_wire_spec=ground_wire_from_record(
            ground_wire, catalog_version=catalog.catalog_version
        ),
    )
    return CrossSectionTransmissionLine(
        name="3L11-example",
        configuration=configuration,
        nominal_voltage=VoltageKV(tower["voltage_kv"], "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )


if __name__ == "__main__":
    line = build_line()
    result = calculate_line_electrical_parameters(
        line,
        st_clair_options=StClairOptions(line_length_start_mi=20, line_length_stop_mi=20),
    )
    print(result.electrical.status)
    print(len(result.st_clair.curves))