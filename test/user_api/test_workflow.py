"""Exercise the optional cross-section calculations and stored-result plots."""

from unittest.mock import patch

import matplotlib
import pytest

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from transmissionlines.user_api import build, plots


@pytest.fixture
def line():
    catalog = build.open_catalog()
    geometry_id = catalog.towers(structure_code="3L11")[0]["record_id"]
    conductor = build.conductor(catalog, record_id="ACSR:1033.5:curlew:standard:54/7", gmr_ft=0.03)
    wire = build.ground_wire(catalog, record_id=catalog.ground_wires(family="ACSR")[0]["record_id"])
    insulator = dict(insulator_type="glass", number_of_insulators=12,
                     insulator_code="U120B", insulator_coupling="ball_and_socket")
    tower = build.tower(
        catalog, geometry_id=geometry_id, name="workflow-tower", ground_wire=wire,
        circuits=[dict(circuit_id=circuit_id, conductor=conductor,
                       bundle=build.bundle(subconductor_count=2, subconductor_spacing_in=18),
                       insulator=insulator) for circuit_id in catalog.tower_circuits(geometry_id)],
    )
    return build.cross_section_line(
        tower, name="workflow-line", voltage_kv=230, frequency_hz=60,
        earth_resistivity_ohm_m=100, everyday_tension_fraction=0.2,
    )


def test_default_computes_electrical_and_curve_and_explains_missing_sag(line) -> None:
    result = build.calculations(line, st_clair_options={"line_length_stop_mi": 20})
    assert result.impedances.circuit_scalars
    assert result.st_clair.curves
    assert result.sag is None
    assert "elastic_modulus_psi" in result.skipped["sag"]
    axes = plots.st_clair(result.st_clair)
    try:
        assert axes.figure.axes
    finally:
        plt.close(axes.figure)


def test_flags_and_sag_options_keep_solvers_independent(line) -> None:
    options = dict(elastic_modulus_psi=11.5e6, thermal_expansion_per_k=19.3e-6,
                   span_start_ft=100, span_stop_ft=200, span_step_ft=50)
    with patch("transmissionlines.user_api.analysis.calculate_electrical", wraps=__import__(
        "transmissionlines.calculations.electrical", fromlist=["calculate_electrical"]
    ).calculate_electrical) as electrical:
        result = build.calculations(line, impedances=False, st_clair_options={"line_length_stop_mi": 20},
                                    sag_options=options, sag_circuit_id=line.configuration.circuits[0].circuit_id)
        assert electrical.call_count == 1
    assert result.impedances is None and result.skipped["impedances"] == "disabled"
    assert result.st_clair is not None and len(result.sag.curves) == 1
    axes = plots.sag(result.sag)
    try:
        assert len(axes.lines) == 1
    finally:
        plt.close(axes.figure)
    disabled = build.calculations(line, impedances=False, st_clair=False, sag=False)
    assert disabled.skipped == dict.fromkeys(("impedances", "st_clair", "sag"), "disabled")
    assert disabled.impedances is disabled.st_clair is disabled.sag is None
    with pytest.raises(ValueError, match="disabled"):
        build.calculations(line, st_clair=False, st_clair_options={})


def test_missing_electrical_keeps_sag_and_invalid_options_raise(line) -> None:
    circuit = line.configuration.circuits[0]
    missing = circuit.conductor_spec.model_copy(update={
        "equipment": circuit.conductor_spec.equipment.model_copy(update={"conductor_gmr": None}),
    })
    configuration = line.configuration.model_copy(update={
        "circuits": [circuit.model_copy(update={"conductor_spec": missing}), *line.configuration.circuits[1:]],
    })
    line = line.model_copy(update={"configuration": configuration})
    options = dict(elastic_modulus_psi=11.5e6, thermal_expansion_per_k=19.3e-6,
                   span_start_ft=100, span_stop_ft=100)
    result = build.calculations(line, sag_options=options)
    assert result.impedances is result.st_clair is None
    assert "conductor_gmr" in result.skipped["impedances"]
    assert "electrical inputs" in result.skipped["st_clair"]
    assert len(result.sag.curves) == 2
    with pytest.raises(ValueError, match="unknown sag_options"):
        build.calculations(line, sag_options={**options, "bad_key": 1})
    with pytest.raises(ValueError, match="extra_forbidden"):
        build.calculations(line, st_clair_options={"unknown": 1})
    with pytest.raises(ValueError, match="disabled"):
        build.calculations(line, sag=False, sag_options=options)


def test_partial_sag_material_mapping_reports_missing_field(line) -> None:
    result = build.calculations(
        line, impedances=False, st_clair=False, sag_options={"elastic_modulus_psi": 11.5e6},
    )
    assert result.sag is None
    assert "thermal_expansion_per_k" in result.skipped["sag"]