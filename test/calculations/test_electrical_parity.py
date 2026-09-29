import json
from pathlib import Path

import numpy as np
import pytest

from transmissionlines.builders.line import ground_wire_from_record, phase_spec_from_record, geometry_from_records
from transmissionlines.calculations.electrical import calculate_line_electrical_parameters
from transmissionlines.catalog.repository import CatalogRepository
from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord, GroundWirePositionRecord, PhasePositionRecord
from transmissionlines.models.assets import CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.common import Bus, GeographicPoint, IdentificationInfo
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.routing import ElectricalTower, LineSpan, RouteGeometry, StartEnd
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.system import TransmissionLineSystem
from transmissionlines.builders.system import assemble_line_into_system
from transmissionlines.units import Angle, BundleSpacing, EarthResistivity, Frequency, VoltageKV

CATALOG = CatalogRepository("data/catalog/v1")

INSULATOR = dict(insulator_type="glass", number_of_insulators=12, insulator_code="U120B", insulator_coupling="ball_and_socket")


def _line(geometry, phases, ground, voltage: int, kind: str):
    configuration = TowerConfiguration(
        name="fixture-configuration", identification_info=IdentificationInfo(),
        geometry=geometry, circuits=phases, ground_wire_spec=ground,
    )
    electrical = dict(
        name="fixture-line", nominal_voltage=VoltageKV(voltage, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    if kind == "cross-section":
        return CrossSectionTransmissionLine(**electrical, configuration=configuration)
    locations = [GeographicPoint(latitude=Angle(45, "degree"), longitude=Angle(value, "degree")) for value in (-108, -107)]
    towers = [
        ElectricalTower(
            name=f"fixture:tower:{index}", tower_id=f"T{index}", sequence=index,
            location=locations[index], configuration=configuration,
            structure_form="pole", support_role="terminal",
        )
        for index in range(2)
    ]
    span = LineSpan(
        name="fixture:span:0", span_id="S0", sequence=0,
        start_end=StartEnd(name="fixture:endpoints", start=towers[0], end=towers[1]),
        route_geometry=RouteGeometry(coordinates=[(-108, 45), (-107, 45)]),
    )
    return RoutedTransmissionLine(
        **electrical, from_bus=Bus(name="from", location=locations[0]),
        to_bus=Bus(name="to", location=locations[1]), spans=[span],
    )


def _calculated(geometry, phases, ground, voltage: int, kind: str, *, options=None, system_path: Path | None = None):
    line = _line(geometry, phases, ground, voltage, kind)
    if system_path is not None:
        system = TransmissionLineSystem()
        assemble_line_into_system(system, line)
        system.to_json(system_path, overwrite=True)
        serialized = system_path.read_text(encoding="utf-8")
        for result_key in ('"line_parameters"', '"matrices"', '"curves"'):
            assert result_key not in serialized
        line = TransmissionLineSystem.from_json(system_path).get_component(type(line), line.name)
    return calculate_line_electrical_parameters(
        line, st_clair_options=options,
    )


def _kersting_inputs():
    code = "EX_K4_1"
    phases = CATALOG.table("phase_positions")
    grounds = CATALOG.table("ground_wire_positions")
    geometry = geometry_from_records(
        [PhasePositionRecord.model_validate(row) for row in phases[phases.geometry_id == code].to_dict("records")],
        [GroundWirePositionRecord.model_validate(row) for row in grounds[grounds.geometry_id == code].to_dict("records")],
    )
    conductors = CATALOG.table("conductors")
    wires = CATALOG.table("ground_wires")
    conductor = conductors[conductors.codeword == "Linnet_EX_K4_1"].iloc[0]
    wire = wires[(wires.family == "ACSR") & (wires.awg_or_stranding == "4/0 6/1")].iloc[0]
    phase = phase_spec_from_record(ConductorRecord.model_validate(conductor.to_dict()), circuit_id="circuit-1", insulator_string=INSULATOR, catalog_version="v1")
    ground = ground_wire_from_record(GroundWireRecord.model_validate(wire.to_dict()), catalog_version="v1")
    return geometry, phase, ground


@pytest.mark.parametrize("kind", ["cross-section", "routed"])
@pytest.mark.parametrize("round_trip", [False, True], ids=["fresh", "reloaded"])
def test_two_circuit_3l11_reference_fixture_matches_all_numeric_outputs(kind: str, round_trip: bool, tmp_path: Path) -> None:
    fixture = json.loads(Path("test/reference/julia/two_circuit_3l11_cardinal.json").read_text(encoding="utf-8"))
    code = "3L11"
    phase_table = CATALOG.table("phase_positions")
    ground_table = CATALOG.table("ground_wire_positions")
    geometry = geometry_from_records(
        [PhasePositionRecord.model_validate(row) for row in phase_table[phase_table.geometry_id == code].to_dict("records")],
        [GroundWirePositionRecord.model_validate(row) for row in ground_table[ground_table.geometry_id == code].to_dict("records")],
    )
    conductors = CATALOG.table("conductors")
    wires = CATALOG.table("ground_wires")
    conductor = ConductorRecord.model_validate(conductors[(conductors.family == "ACSR") & (conductors.codeword == "Cardinal")].iloc[0].to_dict())
    wire = GroundWireRecord.model_validate(wires[(wires.family == "Alumoweld") & (wires.awg_or_stranding == "7/8")].iloc[0].to_dict())
    phases = [
        phase_spec_from_record(conductor, circuit_id=circuit, insulator_string=INSULATOR, subconductor_count=2, subconductor_spacing=BundleSpacing(18, "inch"), catalog_version="v1")
        for circuit in ("circuit-1", "circuit-2")
    ]
    ground = ground_wire_from_record(wire, catalog_version="v1")
    calculated = _calculated(geometry, phases, ground, 345, kind, system_path=tmp_path / "inputs.json" if round_trip else None)
    result = calculated.electrical
    assert result.circuit_ampacity_a == {"circuit-1": 990.0, "circuit-2": 990.0}
    assert result.circuit_subconductor_count == {"circuit-1": 2, "circuit-2": 2}
    assert result.topology == fixture["topology"] == "two-circuit"
    assert result.labels == fixture["labels"]
    assert {item["table_name"] for item in result.provenance} == {"conductors", "ground_wires"}
    for name, expected in fixture["matrices"].items():
        actual = result.matrices[name]
        assert actual.name == expected["name"] == name
        assert actual.row_count == expected["row_count"]
        assert actual.column_count == expected["column_count"]
        assert actual.row_labels == expected["row_labels"]
        assert actual.column_labels == expected["column_labels"]
        assert actual.unit == expected["unit"]
        tolerance = fixture["tolerance"]["shunt"] if name.startswith(("P", "Y")) else fixture["tolerance"]["series"]
        np.testing.assert_allclose(actual.real, expected["real"], rtol=tolerance, atol=1e-12)
        np.testing.assert_allclose(actual.imaginary, expected["imaginary"], rtol=tolerance, atol=1e-12)
    for name, expected in fixture["scalars"].items():
        assert result.scalars[name] == pytest.approx(expected, rel=fixture["tolerance"]["shunt"] if name.startswith("b") else fixture["tolerance"]["scalars"])
        assert result.scalar_units[name] == fixture["scalar_units"][name]
    assert result.scalars["r1"] == pytest.approx(0.06041707268316814, rel=0.005)
    assert result.scalars["x1"] == pytest.approx(0.571814216468555, rel=0.005)
    assert result.scalars["b1"] == pytest.approx(7.540921284378496, rel=0.028)
    assert result.scalars["sil_mw"] == pytest.approx(432.2379746677453, rel=0.005)


@pytest.mark.parametrize("kind", ["cross-section", "routed"])
@pytest.mark.parametrize("round_trip", [False, True], ids=["fresh", "reloaded"])
def test_two_circuit_3l11_st_clair_curve_matches_reference_values(kind: str, round_trip: bool, tmp_path: Path) -> None:
    code = "3L11"
    phase_table = CATALOG.table("phase_positions")
    ground_table = CATALOG.table("ground_wire_positions")
    geometry = geometry_from_records(
        [PhasePositionRecord.model_validate(row) for row in phase_table[phase_table.geometry_id == code].to_dict("records")],
        [GroundWirePositionRecord.model_validate(row) for row in ground_table[ground_table.geometry_id == code].to_dict("records")],
    )
    conductors = CATALOG.table("conductors")
    wires = CATALOG.table("ground_wires")
    conductor = ConductorRecord.model_validate(
        conductors[(conductors.family == "ACSR") & (conductors.codeword == "Cardinal")].iloc[0].to_dict()
    )
    wire = GroundWireRecord.model_validate(
        wires[(wires.family == "Alumoweld") & (wires.awg_or_stranding == "7/8")].iloc[0].to_dict()
    )
    phases = [
        phase_spec_from_record(
            conductor,
            circuit_id=circuit,
            insulator_string=INSULATOR,
            subconductor_count=2,
            subconductor_spacing=BundleSpacing(18, "inch"),
            catalog_version="v1",
        )
        for circuit in ("circuit-1", "circuit-2")
    ]
    ground = ground_wire_from_record(wire, catalog_version="v1")
    options = StClairOptions(
        line_length_start_mi=20.0,
        line_length_stop_mi=600.0,
        line_length_step_mi=20.0,
    )
    result = _calculated(geometry, phases, ground, 345, kind, options=options, system_path=tmp_path / "inputs.json" if round_trip else None).st_clair
    assert result is not None

    assert result.options.r_system_1_ohm == pytest.approx(0.1)
    assert result.options.x_system_1_ohm == pytest.approx(1.0)
    assert result.options.r_system_2_ohm == pytest.approx(0.1)
    assert result.options.x_system_2_ohm == pytest.approx(1.0)
    assert result.options.stability_angle_limit_deg == pytest.approx(45.0)
    assert [curve.circuit_id for curve in result.curves] == ["circuit-1", "circuit-2"]
    expected_lengths = list(range(20, 601, 20))
    sample_indices = [0, 7, 14, 22, 29]
    expected = {
        "pr_mw": [1167.044902685422, 853.2072558576068, 459.90537071393237, 301.4532054048755, 231.7477717169498],
        "ps_mw": [1181.2564507226405, 929.5603650105717, 501.4958615459745, 328.82913348295165, 252.83233709371044],
        "abs_er_pu": [0.9994068441569787, 0.9974563908852275, 0.9994280458710499, 1.0006182712679266, 1.0014064055228944],
        "current_a": [1980.0001764107, 1622.6053554090909, 874.572724151168, 573.0137493016545, 440.3177920670501],
    }
    for curve in result.curves:
        assert curve.lengths_mi == pytest.approx(expected_lengths, abs=1e-12)
        assert curve.limit_type[:6] == ["thermal_ampacity"] * 6
        assert curve.limit_type[6:] == ["steady_state_stability"] * 24
        assert curve.limiting_angle_deg[6:] == pytest.approx([45.0] * 24, abs=1e-12)
        for field, expected_values in expected.items():
            actual_values = [getattr(curve, field)[index] for index in sample_indices]
            assert actual_values == pytest.approx(expected_values, rel=1e-6, abs=1e-6)
        assert [curve.pr_w[index] for index in sample_indices] == pytest.approx([value * 1e6 for value in expected["pr_mw"]], rel=1e-6, abs=1e-6)
        assert [curve.ps_w[index] for index in sample_indices] == pytest.approx([value * 1e6 for value in expected["ps_mw"]], rel=1e-6, abs=1e-6)
        assert [curve.loss_w[index] for index in sample_indices] == pytest.approx([(sent - received) * 1e6 for sent, received in zip(expected["ps_mw"], expected["pr_mw"], strict=True)], rel=1e-6, abs=1e-6)
        assert [curve.abs_er_volt[index] for index in sample_indices] == pytest.approx([value * 345_000 for value in expected["abs_er_pu"]], rel=1e-6, abs=1e-6)


@pytest.mark.parametrize("kind", ["cross-section", "routed"])
@pytest.mark.parametrize("round_trip", [False, True], ids=["fresh", "reloaded"])
def test_33kv_ex_k4_1_single_cardinal_st_clair_curve_matches_reference_values(kind: str, round_trip: bool, tmp_path: Path) -> None:
    code = "EX_K4_1"
    phase_table = CATALOG.table("phase_positions")
    ground_table = CATALOG.table("ground_wire_positions")
    geometry = geometry_from_records(
        [PhasePositionRecord.model_validate(row) for row in phase_table[phase_table.geometry_id == code].to_dict("records")],
        [GroundWirePositionRecord.model_validate(row) for row in ground_table[ground_table.geometry_id == code].to_dict("records")],
    )
    conductors = CATALOG.table("conductors")
    wires = CATALOG.table("ground_wires")
    conductor = ConductorRecord.model_validate(
        conductors[(conductors.family == "ACSR") & (conductors.codeword == "Cardinal")].iloc[0].to_dict()
    )
    wire = GroundWireRecord.model_validate(
        wires[(wires.family == "Alumoweld") & (wires.awg_or_stranding == "7/8")].iloc[0].to_dict()
    )
    phase = phase_spec_from_record(conductor, circuit_id="circuit-1", insulator_string=INSULATOR, subconductor_count=1, catalog_version="v1")
    ground = ground_wire_from_record(wire, catalog_version="v1")
    electrical = _calculated(geometry, [phase], ground, 33, kind).electrical
    assert electrical.topology == "one-circuit"
    options = StClairOptions(
        line_length_start_mi=20.0,
        line_length_stop_mi=600.0,
        line_length_step_mi=20.0,
    )
    result = _calculated(geometry, [phase], ground, 33, kind, options=options, system_path=tmp_path / "inputs.json" if round_trip else None).st_clair
    assert result is not None

    assert result.options.r_system_1_ohm == pytest.approx(0.1)
    assert result.options.x_system_1_ohm == pytest.approx(1.0)
    assert result.options.r_system_2_ohm == pytest.approx(0.1)
    assert result.options.x_system_2_ohm == pytest.approx(1.0)
    assert result.options.stability_angle_limit_deg == pytest.approx(45.0)
    assert result.line_constants[0].nominal_voltage_v == pytest.approx(33_000.0)
    assert result.curves[0].circuit_id == "circuit-1"
    curve = result.curves[0]
    assert curve.lengths_mi == pytest.approx(list(range(20, 601, 20)), abs=1e-12)
    assert curve.limit_type[0] == "thermal_ampacity"
    assert curve.limit_type[1:] == ["steady_state_stability"] * 29
    assert curve.limiting_angle_deg[1:] == pytest.approx([45.0] * 29, abs=1e-12)

    sample_indices = [0, 1, 4, 7, 14, 22, 29]
    expected = {
        "pr_mw": [48.57379371041092, 27.71486599747523, 11.585362105745793, 7.325699747985529, 3.945773096384426, 2.5855806922494247, 1.9874861575623983],
        "ps_mw": [55.47190048313347, 32.46395594974376, 13.681459329341036, 8.669881577310488, 4.677840495629003, 3.0674219912329335, 2.358590280289445],
        "abs_er_pu": [0.9785332722852118, 0.986128271853377, 0.9943454120777848, 0.9967688488971445, 0.9990741571297926, 1.0004099231892352, 1.0012688534074872],
        "current_a": [990.0000333995508, 580.845264569411, 244.05682789794722, 154.50917361814368, 83.27222272061793, 54.55798795087651, 41.92349831451032],
    }
    for field, expected_values in expected.items():
        actual_values = [getattr(curve, field)[index] for index in sample_indices]
        assert actual_values == pytest.approx(expected_values, rel=1e-6, abs=1e-6)
    assert [curve.pr_w[index] for index in sample_indices] == pytest.approx([value * 1e6 for value in expected["pr_mw"]], rel=1e-6, abs=1e-6)
    assert [curve.ps_w[index] for index in sample_indices] == pytest.approx([value * 1e6 for value in expected["ps_mw"]], rel=1e-6, abs=1e-6)
    assert [curve.loss_w[index] for index in sample_indices] == pytest.approx([(sent - received) * 1e6 for sent, received in zip(expected["ps_mw"], expected["pr_mw"], strict=True)], rel=1e-6, abs=1e-6)
    assert [curve.abs_er_volt[index] for index in sample_indices] == pytest.approx([value * 33_000 for value in expected["abs_er_pu"]], rel=1e-6, abs=1e-6)


@pytest.mark.parametrize("kind", ["cross-section", "routed"])
@pytest.mark.parametrize("round_trip", [False, True], ids=["fresh", "reloaded"])
def test_kersting_nontransposed_and_transposed_matrix_outputs(kind: str, round_trip: bool, tmp_path: Path) -> None:
    geometry, phase, ground = _kersting_inputs()
    result = _calculated(geometry, [phase], ground, 33, kind, system_path=tmp_path / "inputs.json" if round_trip else None).electrical

    def matrix(name: str) -> np.ndarray:
        return np.array([[cell["real"] + 1j * cell["imag"] for cell in row] for row in result.matrices[name].cells])

    assert matrix("Zabcg") == pytest.approx(np.array([[.4013+1.4133j, .0953+.8515j, .0953+.7266j, .0953+.7524j], [.0953+.8515j, .4013+1.4133j, .0953+.7802j, .0953+.7865j], [.0953+.7266j, .0953+.7802j, .4013+1.4133j, .0953+.7674j], [.0953+.7524j, .0953+.7865j, .0953+.7674j, .6873+1.5465j]]), rel=0.005)
    assert matrix("Z_kron_nt") == pytest.approx(np.array([[.4576+1.0780j, .1560+.5017j, .1535+.3849j], [.1560+.5017j, .4666+1.0482j, .1580+.4236j], [.1535+.3849j, .1580+.4236j, .4615+1.0651j]]), rel=0.005)
    assert matrix("Z_kron_ft") == pytest.approx(np.array([[.4619+1.0638j, .1558+.4368j, .1558+.4368j], [.1558+.4368j, .4619+1.0638j, .1558+.4368j], [.1558+.4368j, .1558+.4368j, .4619+1.0638j]]), rel=0.005)
    assert matrix("Z012_ft") == pytest.approx(np.diag([.7735+1.9373j, .3061+.6270j, .3061+.6270j]), rel=0.005)
    assert matrix("Y_kron_nt") == pytest.approx(np.array([[5.6711j, -1.8362j, -.7033j], [-1.8362j, 5.9774j, -1.169j], [-.7033j, -1.169j, 5.3911j]]), rel=0.028)
    assert matrix("Z012_nt") == pytest.approx(np.array([[.77354+1.93759j, .02556+.01149j, -.03209+.01589j], [-.03209+.01589j, .30607+.62736j, -.07225-.00603j], [.02556+.01149j, .07230-.00590j, .30607+.62736j]]), rel=0.005)
    assert matrix("Y012_nt") == pytest.approx(np.array([[3.14339j, -.15758-.03302j, .15758-.03302j], [.15758-.03302j, 6.91344j, .82280+.06243j], [-.15758-.03302j, -.82280+.06243j, 6.91344j]]), rel=0.028)
    assert matrix("Y012_ft") == pytest.approx(np.diag([3.14339j, 6.91344j, 6.91344j]), rel=0.028)
    assert result.scalars["surge_impedance_ohm"] == pytest.approx(301.24, rel=0.005)
    assert result.scalars["sil_mw"] == pytest.approx(3.6151, rel=0.005)
    assert result.matrices["Z_kron"] is result.matrices["Z_kron_nt"]


@pytest.mark.parametrize("kind", ["cross-section", "routed"])
def test_input_system_round_trip_recalculates_without_persisting_results(kind: str, tmp_path: Path) -> None:
    geometry, phase, ground = _kersting_inputs()
    line = _line(geometry, [phase], ground, 33, kind)
    options = StClairOptions(line_length_start_mi=20, line_length_stop_mi=20)
    before = calculate_line_electrical_parameters(line, st_clair_options=options)
    system = TransmissionLineSystem()
    assemble_line_into_system(system, line)
    path = tmp_path / "inputs.json"
    system.to_json(path, overwrite=True)
    serialized = path.read_text(encoding="utf-8")
    assert '"st_clair_curve"' not in serialized
    assert '"line_parameters"' not in serialized
    assert '"matrices"' not in serialized
    assert '"curves"' not in serialized
    loaded = TransmissionLineSystem.from_json(path)
    restored = loaded.get_component(type(line), line.name)
    after = calculate_line_electrical_parameters(restored, st_clair_options=options)
    assert after.electrical.labels == before.electrical.labels
    assert after.electrical.scalar_units == before.electrical.scalar_units
    assert after.electrical.scalars == pytest.approx(before.electrical.scalars)
    for name in before.electrical.matrices:
        assert after.electrical.matrices[name].unit == before.electrical.matrices[name].unit
        np.testing.assert_allclose(after.electrical.matrices[name].real, before.electrical.matrices[name].real, rtol=1e-12)
        np.testing.assert_allclose(after.electrical.matrices[name].imaginary, before.electrical.matrices[name].imaginary, rtol=1e-12)
    assert after.st_clair is not None and before.st_clair is not None
    assert after.st_clair.curves[0].pr_w == pytest.approx(before.st_clair.curves[0].pr_w)
    assert after.st_clair.curves[0].limit_type == before.st_clair.curves[0].limit_type
