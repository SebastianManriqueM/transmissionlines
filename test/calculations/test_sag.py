import math

import matplotlib
import matplotlib.pyplot as plt
import pytest
from pydantic import ValidationError

from transmissionlines.calculations.sag import calculate_sag
from transmissionlines.plotting.sag import plot_sag_curve
from transmissionlines.calculations import constants
from transmissionlines.calculations import sag as sag_module
from transmissionlines.calculations.sag import solve_span_sag
from transmissionlines.models.cables import BareConductorEquipment
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.geometry import PhasePosition, TowerGeometry
from transmissionlines.models.sag import SagCurveResult, SagOptions
from transmissionlines.units import Quantity
from test.integration.test_line_electrical_orchestration import _circuit, _line


def _options(**overrides: object) -> SagOptions:
    values = {"elastic_modulus_psi": 11.5e6,
              "thermal_expansion_per_k": 19.3e-6, **overrides}
    return SagOptions(**values)


def _mechanical_line():
    line = _line()
    line.configuration.circuits[0].conductor_spec.equipment = BareConductorEquipment(
        weight_lb_kft=656,
        rated_strength_lb=19500,
        total_area_in2=0.435,
    )
    return line


def test_solver_numerical_limits_are_named() -> None:
    assert constants.SAG_MAX_BRACKET_STEPS == 1024
    assert constants.SAG_MAX_BISECTION_STEPS == 256
    assert constants.SAG_RELATIVE_LENGTH_TOLERANCE == 1e-11
    assert constants.SAG_RELATIVE_TENSION_TOLERANCE == 1e-10
    assert constants.ST_CLAIR_BOUNDARY_REFINEMENT_STEPS == 18


def test_options_require_physical_quantities_and_convert_mixed_units() -> None:
    defaults = _options()
    assert defaults.reference_temperature_c == pytest.approx(25)
    assert defaults.operating_temperature_c == pytest.approx(75)
    assert defaults.span_start_ft == pytest.approx(20)
    assert defaults.span_stop_ft == pytest.approx(2000)
    assert defaults.span_step_ft == pytest.approx(10)
    assert defaults.elevation_difference_ft == pytest.approx(0)
    line = _mechanical_line()
    line.everyday_tension_fraction = 0.2
    mixed = _options(
        reference_temperature_c=Quantity(77, "degF"),
        operating_temperature_c=Quantity(348.15, "kelvin"),
        span_start_ft=Quantity(121.92, "meter"),
        span_stop_ft=400,
        span_step_ft=Quantity(3.048, "meter"),
        elevation_difference_ft=Quantity(30.48, "meter"),
    )
    result = calculate_sag(line, options=mixed)
    expected = calculate_sag(line, options=_options(
        span_start_ft=400, span_stop_ft=400,
        elevation_difference_ft=100,
    ))
    assert result.curves[0].span_lengths_ft == pytest.approx([400])
    assert result.curves[0].sag_ft == pytest.approx(expected.curves[0].sag_ft)
    restored = SagCurveResult.model_validate_json(result.model_dump_json())
    assert restored.options.elevation_difference_ft == pytest.approx(100)
    for field in ("reference_temperature", "operating_temperature", "span_start", "span_stop", "span_step", "elevation_difference"):
        with pytest.raises(ValidationError, match=field):
            _options(**{field: 25.0})


def test_default_cross_section_grid_and_reference_sag() -> None:
    line = _mechanical_line()
    options = _options(operating_temperature_c=25)

    with pytest.warns(UserWarning, match="20%"):
        result = calculate_sag(line, options=options)

    curve = result.curves[0]
    assert len(curve.span_lengths_ft) == 199
    assert curve.span_lengths_ft[:2] == [20, 30]
    assert curve.span_lengths_ft[-1] == 2000
    assert curve.horizontal_tension_lb == pytest.approx([3900] * 199)
    assert curve.sag_ft[38] == pytest.approx(
        3900 / 0.656 * (math.cosh(0.656 * 400 / (2 * 3900)) - 1)
    )
    assert result.everyday_tension_fraction == pytest.approx(0.2)
    assert result.warnings


@pytest.mark.parametrize("rise", [0.0, 120.0, -120.0])
@pytest.mark.parametrize("strain", [0.0, 0.0006])
def test_span_solver_matches_independent_reference_length_and_chord_maximum(rise: float, strain: float) -> None:
    weight, reference_tension, area, modulus = 0.656, 3900.0, 0.435, 11.5e6
    sag, position, tension = solve_span_sag(
        weight, 19500, area_in2=area, modulus_psi=modulus,
        expansion_per_c=19.3e-6, reference_fraction=0.2, span_ft=400,
        rise_ft=rise, reference_temperature_c=25, operating_temperature_c=75,
        additional_permanent_strain=strain,
    )
    length = lambda force: math.hypot(2 * force / weight * math.sinh(400 * weight / (2 * force)), rise)
    unstressed = length(reference_tension) / (1 + reference_tension / (modulus * area))
    target = unstressed * (1 + strain) * (1 + 19.3e-6 * 50) * (1 + tension / (modulus * area))
    assert length(tension) == pytest.approx(target, rel=1e-11)
    assert 0 < position < 400
    parameter = tension / weight
    vertex = 200 - parameter * math.asinh(rise / (2 * parameter * math.sinh(200 / parameter)))
    def chord_drop(horizontal: float) -> float:
        return rise * horizontal / 400 - parameter * (
            math.cosh((horizontal - vertex) / parameter) - math.cosh(vertex / parameter)
        )
    sampled_max = max(chord_drop(index / 4) for index in range(1601))
    assert sag == pytest.approx(sampled_max, abs=1e-4)
    assert chord_drop(0) == pytest.approx(0, abs=1e-9)
    assert chord_drop(400) == pytest.approx(0, abs=1e-9)


def test_permanent_strain_at_reference_temperature_still_changes_tension() -> None:
    common = dict(area_in2=0.435, modulus_psi=11.5e6, expansion_per_c=19.3e-6,
                  reference_fraction=0.2, span_ft=400, rise_ft=0,
                  reference_temperature_c=25, operating_temperature_c=25)
    reference = solve_span_sag(0.656, 19500, **common)
    strained = solve_span_sag(0.656, 19500, additional_permanent_strain=0.0006, **common)
    assert reference[2] == 3900
    assert strained[2] < reference[2]
    assert strained[0] > reference[0]


def test_custom_grid_exact_endpoint_and_bundle_uses_one_conductor() -> None:
    line = _mechanical_line()
    line.everyday_tension_fraction = 0.30
    base = calculate_sag(line, options=_options(span_start_ft=21, span_stop_ft=42))
    line.configuration.circuits[0].bundle_spec = line.configuration.circuits[0].bundle_spec.model_copy(
        update={"subconductor_count": 2, "subconductor_spacing_in": 18}
    )
    result = calculate_sag(line, options=_options(span_start_ft=21, span_stop_ft=42, span_step_ft=10))
    assert len(result.curves) == 1
    assert result.curves[0].span_lengths_ft == [21, 31, 41, 42]
    assert result.curves[0].horizontal_tension_lb[0] < 5850
    assert result.curves[0].sag_ft[0] == pytest.approx(base.curves[0].sag_ft[0])
    assert result.everyday_tension_fraction == pytest.approx(0.30)
    assert not result.warnings


def test_custom_grid_preserves_short_interval_beyond_absolute_tolerance() -> None:
    line = _mechanical_line()
    line.everyday_tension_fraction = 0.2
    result = calculate_sag(line, options=_options(span_stop_ft=2000.000001))

    assert len(result.curves[0].span_lengths_ft) == 200
    assert result.curves[0].span_lengths_ft[-2:] == [2000, 2000.000001]


def test_all_circuits_and_explicit_selection_preserve_conductor_identity() -> None:
    line = _mechanical_line()
    line.everyday_tension_fraction = 0.2
    other = _circuit("c2", BareConductorEquipment(
        weight_lb_kft=800,
        rated_strength_lb=22000,
        total_area_in2=0.5,
    ))
    phases = [*line.configuration.geometry.phase_positions, *[
        PhasePosition(circuit_id="c2", phase=phase, x_ft=index * 4, y_ft=30)
        for index, phase in enumerate(("A", "B", "C"), start=4)
    ]]
    line.configuration = TowerConfiguration(
        name="two-circuit", identification_info=line.configuration.identification_info,
        geometry=TowerGeometry(phase_positions=phases,
                               ground_wire_positions=line.configuration.geometry.ground_wire_positions),
        ground_wire_spec=line.configuration.ground_wire_spec,
        circuits=[other, *line.configuration.circuits],
    )
    options = _options(span_start_ft=400, span_stop_ft=400, operating_temperature_c=25)
    result = calculate_sag(line, options=options)
    assert [curve.circuit_id for curve in result.curves] == ["c1", "c2"]
    assert result.curves[0].horizontal_tension_lb == [3900]
    assert result.curves[1].horizontal_tension_lb[0] != result.curves[0].horizontal_tension_lb[0]
    assert result.curves[1].conductor_uuid == other.conductor_spec.uuid
    assert [curve.circuit_id for curve in calculate_sag(line, options=options, circuit_id="c2").curves] == ["c2"]
    with pytest.raises(ValueError, match="unknown circuit_id"):
        calculate_sag(line, options=options, circuit_id="absent")


@pytest.mark.parametrize("field", ["weight_lb_kft", "rated_strength_lb", "total_area_in2"])
def test_missing_mechanics_identifies_circuit_and_field(field: str) -> None:
    line = _mechanical_line()
    line.configuration.circuits[0].conductor_spec.equipment = line.configuration.circuits[0].conductor_spec.equipment.model_copy(update={field: None})
    with pytest.warns(UserWarning, match="20%"):
        with pytest.raises(ValueError, match=f"circuit c1: {field}"):
            calculate_sag(line, options=_options(span_stop_ft=20))


def test_options_and_line_tension_reject_invalid_inputs() -> None:
    with pytest.raises(ValidationError, match="convertible to 1 / kelvin"):
        _options(thermal_expansion_per_k=Quantity(1, "pound_force / kilofoot"))
    with pytest.raises(ValidationError, match="elastic_modulus"):
        _options(elastic_modulus_psi=0)
    with pytest.raises(ValidationError, match="span lengths"):
        _options(span_step_ft=0)
    with pytest.raises(ValidationError, match="sag options must be finite"):
        _options(elevation_difference_ft=float("nan"))
    line = _mechanical_line()
    with pytest.raises(ValidationError, match="everyday_tension_fraction"):
        line.everyday_tension_fraction = 0.31


def test_span_solver_reports_overflow() -> None:
    common = dict(area_in2=0.435, modulus_psi=11.5e6, reference_fraction=0.2,
                  span_ft=400, rise_ft=0, reference_temperature_c=25,
                  operating_temperature_c=75)
    with pytest.raises(ValueError, match="overflow"):
        solve_span_sag(0.656, 19500, expansion_per_c=19.3e-6, **{**common, "span_ft": 10_000_000})


def test_span_solver_reports_nonconvergence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sag_module, "SAG_MAX_BISECTION_STEPS", 1)
    with pytest.raises(ValueError, match="horizontal tension solver did not converge"):
        solve_span_sag(
            0.656, 19500, area_in2=0.435, modulus_psi=11.5e6,
            expansion_per_c=19.3e-6, reference_fraction=0.2, span_ft=400,
            rise_ft=0, reference_temperature_c=25, operating_temperature_c=75,
        )


def test_public_plot_and_result_round_trip() -> None:
    matplotlib.use("Agg")
    line = _mechanical_line()
    line.everyday_tension_fraction = 0.2
    result = calculate_sag(line, options=_options(span_stop_ft=40))
    restored = SagCurveResult.model_validate_json(result.model_dump_json())
    axes = plot_sag_curve(restored, circuit_id="c1")

    assert restored.options.elastic_modulus_psi == pytest.approx(11.5e6)
    assert restored.curves[0].conductor_uuid == line.configuration.circuits[0].conductor_spec.uuid
    assert axes.lines[0].get_xdata().tolist() == [20, 30, 40]
    assert axes.get_xlabel() == "Horizontal span (ft)"
    assert axes.get_ylabel() == "Maximum chord-relative sag (ft)"
    assert "Conductor unspecified | stranding unspecified" in axes.texts[0].get_text()
    assert axes.xaxis.label.get_size() == 14
    assert axes.yaxis.label.get_size() == 14
    assert axes.title.get_size() == 16
    assert all(label.get_size() == 14 for label in axes.get_xticklabels() + axes.get_yticklabels())
    assert all(text.get_fontsize() == 14 for text in axes.get_legend().get_texts())
    assert axes.lines[0].get_linewidth() == pytest.approx(2.5)
    with pytest.raises(ValueError, match="unknown circuit_id"):
        plot_sag_curve(restored, circuit_id="missing")
    plt.close(axes.figure)