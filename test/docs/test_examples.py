import subprocess
import sys

from transmissionlines.api import calculate_line_electrical_parameters, calculate_st_clair_curve
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.units import (
    CableDiameter,
    CableGMR,
    Current,
    EarthResistivity,
    Frequency,
    ResistancePerKft,
    TowerCoordinate,
    VoltageKV,
)


def _quickstart_line() -> CrossSectionTransmissionLine:
    conductor = BareConductorEquipment(
        conductor_diameter=CableDiameter(1, "inch"),
        conductor_gmr=CableGMR(0.04, "foot"),
        ampacity=Current(1000, "ampere"),
        ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
        dc_resistance=ResistancePerKft(0.2, "ohm / kilofoot"),
    )
    geometry = TowerGeometry(
        phase_positions=[
            PhasePosition(
                circuit_id="c1",
                phase=phase,
                x=TowerCoordinate(index * 4, "foot"),
                y=TowerCoordinate(30, "foot"),
            )
            for index, phase in enumerate(("A", "B", "C"))
        ],
        ground_wire_positions=[
            GroundWirePosition(
                wire_id="g1",
                x=TowerCoordinate(0, "foot"),
                y=TowerCoordinate(40, "foot"),
            )
        ],
    )
    configuration = TowerConfiguration(
        name="example-configuration",
        identification_info=IdentificationInfo(),
        geometry=geometry,
        ground_wire_spec=GroundWireSpec(name="ground", equipment=conductor),
        circuits=[CircuitConfiguration(
            name="c1", circuit_id="c1",
            conductor_spec=ConductorSpec(name="phase", equipment=conductor),
            bundle_spec=BundleSpec(subconductor_count=1),
            insulator_string=InsulatorStringSpec(
                insulator_type="glass", number_of_insulators=12,
                insulator_code="U120B", insulator_coupling="ball_and_socket",
            ),
        )],
    )
    return CrossSectionTransmissionLine(
        name="example-line", configuration=configuration,
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )


def test_quickstart_in_memory_line_example() -> None:
    line = _quickstart_line()
    calculated = calculate_line_electrical_parameters(
        line,
        st_clair_options=StClairOptions(
            line_length_start_mi=20.0,
            line_length_stop_mi=20.0,
        ),
    )

    electrical = calculated.electrical
    assert electrical.status == "complete"
    assert electrical.matrices["Zabcg"].row_count == 4
    assert electrical.matrices["Z012_ft"].row_labels == [
        "1:zero",
        "1:positive",
        "1:negative",
    ]
    assert electrical.scalars["r1"] > 0.0
    assert calculated.st_clair.curves[0].lengths_mi == [20.0]
    assert "line_parameters" not in type(line).model_fields


def test_quickstart_direct_st_clair_example() -> None:
    result = calculate_st_clair_curve(
        positive_sequence={
            "circuit_id": "example",
            "nominal_voltage_kv": 345.0,
            "r_ohm_per_mile": 0.0012,
            "x_ohm_per_mile": 0.012,
            "b_siemens_per_mile": 0.0008,
            "conductor_ampacity_a": 1000.0,
        },
        options=StClairOptions(
            line_length_start_mi=20.0,
            line_length_stop_mi=20.0,
        ),
    )

    assert len(result.curves) == 1
    assert result.curves[0].circuit_id == "example"
    assert result.curves[0].lengths_mi == [20.0]
    assert result.curves[0].pr_mw[0] > 0.0
    assert result.units["power"] == "W and MW"


def test_catalog_backed_line_example_uses_default_v2() -> None:
    completed = subprocess.run(
        [sys.executable, "docs/source/how-to/examples/catalog_line.py"],
        capture_output=True, text=True, check=True,
    )

    assert completed.stdout.splitlines() == ["complete", "2"]


def test_catalog_backed_sag_example() -> None:
    completed = subprocess.run(
        [sys.executable, "docs/source/how-to/examples/sag_curve.py"],
        capture_output=True, text=True, check=True,
    )
    assert completed.stdout.splitlines() == ["2", "199"]