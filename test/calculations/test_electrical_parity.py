import json
from pathlib import Path

import numpy as np
import pytest

from transmissionlines.builders.line import ground_wire_from_record, phase_spec_from_record, geometry_from_records
from transmissionlines.calculations.electrical import calculate_electrical
from transmissionlines.calculations.st_clair import calculate_st_clair
from transmissionlines.catalog.repository import CatalogRepository
from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord, GroundWirePositionRecord, PhasePositionRecord
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.units import BundleSpacing, Frequency, VoltageKV

CATALOG = CatalogRepository("data/catalog/v1")


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
    phase = phase_spec_from_record(ConductorRecord.model_validate(conductor.to_dict()), circuit_id="circuit-1", catalog_version="v1")
    ground = ground_wire_from_record(GroundWireRecord.model_validate(wire.to_dict()), catalog_version="v1")
    return geometry, phase, ground


def test_two_circuit_3l11_reference_fixture_matches_all_numeric_outputs() -> None:
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
        phase_spec_from_record(conductor, circuit_id=circuit, subconductor_count=2, subconductor_spacing=BundleSpacing(18, "inch"), catalog_version="v1")
        for circuit in ("circuit-1", "circuit-2")
    ]
    ground = ground_wire_from_record(wire, catalog_version="v1")
    result = calculate_electrical(geometry, phase_specs=phases, ground_wire_spec=ground, voltage=VoltageKV(345, "kilovolt"), frequency=Frequency(60, "hertz"), earth_resistivity=100.0)
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


def test_two_circuit_3l11_st_clair_curve_matches_reference_values() -> None:
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
            subconductor_count=2,
            subconductor_spacing=BundleSpacing(18, "inch"),
            catalog_version="v1",
        )
        for circuit in ("circuit-1", "circuit-2")
    ]
    ground = ground_wire_from_record(wire, catalog_version="v1")
    electrical = calculate_electrical(
        geometry,
        phase_specs=phases,
        ground_wire_spec=ground,
        voltage=VoltageKV(345, "kilovolt"),
        frequency=Frequency(60, "hertz"),
        earth_resistivity=100.0,
    )
    st_clair_inputs = [
        {
            "circuit_id": circuit_id,
            "nominal_voltage_kv": 345.0,
            "r_ohm_per_mile": values["r1"],
            "x_ohm_per_mile": values["x1"],
            "b_microsiemens_per_mile": values["b1"],
            "conductor_ampacity_a": 990.0,
            "subconductor_count": 2,
        }
        for circuit_id, values in electrical.circuit_scalars.items()
    ]
    options = StClairOptions(
        line_length_start_mi=20.0,
        line_length_stop_mi=600.0,
        line_length_step_mi=20.0,
    )
    result = calculate_st_clair(st_clair_inputs, options=options)

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


def test_33kv_ex_k4_1_single_cardinal_st_clair_curve_matches_reference_values() -> None:
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
    phase = phase_spec_from_record(conductor, circuit_id="circuit-1", subconductor_count=1, catalog_version="v1")
    ground = ground_wire_from_record(wire, catalog_version="v1")
    electrical = calculate_electrical(
        geometry,
        phase_specs=[phase],
        ground_wire_spec=ground,
        voltage=VoltageKV(33, "kilovolt"),
        frequency=Frequency(60, "hertz"),
        earth_resistivity=100.0,
    )
    assert electrical.topology == "one-circuit"
    source = {
        "circuit_id": "circuit-1",
        "nominal_voltage_kv": 33.0,
        "r_ohm_per_mile": electrical.scalars["r1"],
        "x_ohm_per_mile": electrical.scalars["x1"],
        "b_microsiemens_per_mile": electrical.scalars["b1"],
        "conductor_ampacity_a": 990.0,
        "subconductor_count": 1,
    }
    options = StClairOptions(
        line_length_start_mi=20.0,
        line_length_stop_mi=600.0,
        line_length_step_mi=20.0,
    )
    result = calculate_st_clair(source, options=options)

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


def test_kersting_nontransposed_and_transposed_matrix_outputs() -> None:
    geometry, phase, ground = _kersting_inputs()
    result = calculate_electrical(geometry, phase_specs=[phase], ground_wire_spec=ground, voltage=VoltageKV(33, "kilovolt"), frequency=Frequency(60, "hertz"), earth_resistivity=100.0)

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
