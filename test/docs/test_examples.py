from transmissionlines.api import calculate_line_electrical_parameters, calculate_st_clair_curve
from transmissionlines.models.assets import LineTechnicalInfo, TransmissionLine
from transmissionlines.models.cables import BareConductorEquipment, GroundWireSpec, PhaseConductorSpec
from transmissionlines.models.common import Bus, GeographicPoint, IdentificationInfo
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.units import (
    Angle,
    CableDiameter,
    CableGMR,
    Current,
    EarthResistivity,
    Frequency,
    ResistancePerKft,
    TowerCoordinate,
    VoltageKV,
)


def _quickstart_line() -> TransmissionLine:
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
        ground_wire_spec=GroundWireSpec(conductor=conductor),
        phase_conductor_specs=[PhaseConductorSpec(conductor=conductor, circuit_id="c1")],
    )
    origin = GeographicPoint(latitude=Angle(0, "degree"), longitude=Angle(0, "degree"))
    destination = GeographicPoint(latitude=Angle(1, "degree"), longitude=Angle(1, "degree"))
    technical_info = LineTechnicalInfo(
        line_name="example-line",
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
        from_bus=Bus(name="from", location=origin),
        to_bus=Bus(name="to", location=destination),
    )
    return TransmissionLine(
        name="example-line",
        technical_info=technical_info,
        tower_configuration=configuration,
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

    electrical = calculated.line_parameters.electrical_parameters
    assert electrical.status == "complete"
    assert electrical.matrices["Zabcg"].row_count == 4
    assert electrical.matrices["Z012_ft"].row_labels == [
        "1:zero",
        "1:positive",
        "1:negative",
    ]
    assert electrical.scalars["r1"] > 0.0
    assert electrical.st_clair_curve.curves[0].lengths_mi == [20.0]
    assert line.line_parameters is None


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