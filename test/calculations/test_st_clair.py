import pytest
import builtins

from transmissionlines.calculations.st_clair import (
    _solve_mesh,
    calculate_st_clair,
    nominal_pi_to_equivalent_pi,
)
from transmissionlines.api import calculate_st_clair_curve, plot_st_clair_curve
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.plotting.st_clair import plot_st_clair_curve as plot_st_clair_result


def _input(**overrides: float) -> dict[str, float | str]:
    return {
        "circuit_id": "c1",
        "nominal_voltage_kv": 345.0,
        "r_ohm_per_mile": 0.0012,
        "x_ohm_per_mile": 0.012,
        "b_microsiemens_per_mile": 800.0,
        "conductor_ampacity_a": 1000.0,
        "subconductor_count": 2,
        **overrides,
    }


def test_default_options_and_explicit_constants_use_natural_units() -> None:
    options = StClairOptions(line_length_start_mi=20.0, line_length_stop_mi=20.0)

    assert options.abs_e1_pu == 1.0
    assert options.abs_e2_pu == 1.0
    assert options.r_system_1_ohm == pytest.approx(0.1)
    assert options.r_system_2_ohm == pytest.approx(0.1)
    assert options.x_system_1_ohm == pytest.approx(1.0)
    assert options.x_system_2_ohm == pytest.approx(1.0)
    assert options.n_s_percent == 0.0
    assert options.n_r_percent == 0.0
    assert options.n_series_percent == 0.0
    assert options.receiving_voltage_limit_pu == 0.95
    assert options.stability_angle_limit_deg == 45.0
    assert options.angle_step_deg == 0.5

    result = calculate_st_clair(
        positive_sequence=_input(b_siemens_per_mile=0.0008),
        options=options,
    )

    assert result.line_constants[0].nominal_voltage_v == pytest.approx(345_000.0)
    assert result.line_constants[0].e1_v == pytest.approx(345_000.0)
    assert result.line_constants[0].e2_v == pytest.approx(345_000.0)
    assert result.line_constants[0].b_siemens_per_mile == pytest.approx(0.0008)
    assert result.curves[0].circuit_nominal_ampacity_a == pytest.approx(2000.0)
    assert result.curves[0].thermal_power_mw == pytest.approx(
        3**0.5 * 345_000.0 * 2000.0 / 1e6
    )


def test_b1_microsiemens_per_mile_converts_to_siemens_per_mile() -> None:
    options = StClairOptions(line_length_start_mi=20, line_length_stop_mi=20)
    result = calculate_st_clair(_input(), options=options)
    assert result.line_constants[0].b_siemens_per_mile == pytest.approx(800e-6)


def test_direct_input_requires_conductor_ampacity() -> None:
    source = _input()
    source.pop("conductor_ampacity_a")

    with pytest.raises(ValueError, match="conductor_ampacity_a is required"):
        calculate_st_clair(source)


def test_system_resistance_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match="system resistances cannot be negative"):
        StClairOptions(r_system_1_ohm=-0.01)


def test_stability_boundary_uses_exact_configured_angle() -> None:
    options = StClairOptions(
        line_length_start_mi=20,
        line_length_stop_mi=20,
        stability_angle_limit_deg=1.3,
        angle_step_deg=0.5,
    )
    result = calculate_st_clair(_input(conductor_ampacity_a=1e9), options=options)

    assert result.curves[0].limit_type == ["steady_state_stability"]
    assert result.curves[0].limiting_angle_deg == pytest.approx([1.3])


@pytest.mark.parametrize(
    "y_s,y_r",
    [(0.0 + 0.001j, 0.0 + 0.001j), (0.0 + 0.0007j, 0.0 + 0.0013j)],
    ids=["symmetric", "unequal-shunt"],
)
def test_equivalent_pi_round_trips_abcd(y_s: complex, y_r: complex) -> None:
    z_s = 0.4 + 4.2j
    z_eq, ys_eq, yr_eq = nominal_pi_to_equivalent_pi(z_s, y_s, y_r)
    actual = (
        1 + z_s * y_r,
        z_s,
        y_s + y_r + y_s * z_s * y_r,
        1 + z_s * y_s,
    )
    reconstructed = (
        1 + z_eq * yr_eq,
        z_eq,
        ys_eq + yr_eq + ys_eq * z_eq * yr_eq,
        1 + z_eq * ys_eq,
    )
    assert reconstructed == pytest.approx(actual)
    assert ys_eq != yr_eq if y_s != y_r else ys_eq == yr_eq


def test_mesh_power_loss_identity_and_sensitivity_serialization() -> None:
    options = StClairOptions(line_length_start_mi=20, line_length_stop_mi=20)
    constants = calculate_st_clair(_input(), options=options).line_constants[0]
    point = _solve_mesh(constants, options, 20, 10)
    long_point = _solve_mesh(constants, options, 600, 10)
    assert point["z_line"] == pytest.approx(complex(constants.r_ohm_per_mile * 20, constants.x_ohm_per_mile * 20))
    assert long_point["z_line"] == pytest.approx(point["z_line"] * 30)
    assert point["ps_w"] - point["pr_w"] == pytest.approx(point["series_loss_w"], rel=1e-8)
    z_system_1 = complex(options.r_system_1_ohm, options.x_system_1_ohm)
    z_system_2 = complex(options.r_system_2_ohm, options.x_system_2_ohm)
    assert point["es"] == pytest.approx(point["e1"] - z_system_1 * point["i1"])
    assert point["er"] == pytest.approx(point["e2"] + z_system_2 * point["i3"])
    assert point["es"] == pytest.approx(point["z_s"] * (point["i1"] - point["i2"]))
    assert point["er"] == pytest.approx(point["z_r"] * (point["i2"] - point["i3"]))

    result = calculate_st_clair(_input(), options=options, sensitivities={"n_series_percent": [0, 10]})
    assert len(result.sensitivity_curves) == 2
    assert result.sensitivity_curves[0].name == "n_series_percent=0"
    restored = type(result).model_validate_json(result.model_dump_json())
    assert restored.curves[0].lengths_mi == [20]
    assert len(restored.curves[0].limit_type) == 1
    assert restored.units["susceptance_per_mile"] == "S/mile"


def test_public_explicit_api_and_numerical_import_do_not_require_plotting(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def reject_matplotlib(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("matplotlib"):
            raise ImportError("plotting intentionally unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_matplotlib)
    result = calculate_st_clair_curve(
        positive_sequence=_input(),
        options=StClairOptions(line_length_start_mi=20, line_length_stop_mi=20),
    )
    assert result.curves[0].circuit_id == "c1"


def test_plotting_returns_axes_with_noninteractive_backend() -> None:
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    result = calculate_st_clair(_input(), options=StClairOptions(line_length_start_mi=20, line_length_stop_mi=20))
    axes = plot_st_clair_result(result, show_limits=True)
    assert axes.get_xlabel() == "Line length (mi)"
    assert axes.xaxis.label.get_size() == 14
    assert axes.yaxis.label.get_size() == 14
    assert axes.title.get_size() == 16
    assert all(label.get_size() == 14 for label in axes.get_xticklabels() + axes.get_yticklabels())
    assert all(text.get_fontsize() == 14 for text in axes.get_legend().get_texts())
    assert axes.lines[0].get_ydata().size == 1
    assert axes.lines[0].get_linewidth() == pytest.approx(2.5)
    plt.close(axes.figure)


def test_plotting_shows_voltage_limit_when_stability_is_binding() -> None:
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    source = _input(
        r_ohm_per_mile=0.06041707268316814,
        x_ohm_per_mile=0.571814216468555,
        b_microsiemens_per_mile=7.540921284378496,
        conductor_ampacity_a=990.0,
    )
    options = StClairOptions(
        stability_angle_limit_deg=35.0,
        line_length_start_mi=20.0,
        line_length_stop_mi=600.0,
        line_length_step_mi=20.0,
    )
    result = calculate_st_clair(
        [source, {**source, "circuit_id": "c2"}],
        options=options,
    )
    curve = result.curves[0]

    assert "steady_state_stability" in curve.limit_type
    assert "voltage_drop" not in curve.limit_type
    assert min(curve.abs_er_pu) > options.receiving_voltage_limit_pu
    assert max(curve.abs_er_pu) > min(curve.abs_er_pu)

    axes = plot_st_clair_curve(result, show_voltage_limit=True)
    voltage_axes = axes.figure.axes[1]
    voltage_lines = {line.get_label(): line for line in voltage_axes.lines}
    legend_labels = [text.get_text() for text in axes.get_legend().get_texts()]

    assert voltage_axes.get_ylabel() == "Receiving-end voltage (pu)"
    assert voltage_axes.yaxis.label.get_size() == 14
    assert all(label.get_size() == 14 for label in voltage_axes.get_yticklabels())
    assert voltage_lines["c1: receiving-end voltage"].get_ydata() == pytest.approx(curve.abs_er_pu)
    assert voltage_lines["c1: receiving-end voltage"].get_linewidth() == pytest.approx(2.5)
    assert voltage_lines["Voltage-drop limit (0.95 pu)"].get_linewidth() == pytest.approx(2.5)
    assert "c2: receiving-end voltage" in voltage_lines
    assert voltage_lines["Voltage-drop limit (0.95 pu)"].get_ydata() == pytest.approx([0.95, 0.95])
    assert len(legend_labels) == len(set(legend_labels))
    plt.close(axes.figure)


@pytest.mark.parametrize(
    "options,limit",
    [
        (StClairOptions(line_length_start_mi=20, line_length_stop_mi=20, abs_e2_pu=0.5), "voltage_drop"),
        (StClairOptions(line_length_start_mi=20, line_length_stop_mi=20, stability_angle_limit_deg=1), "steady_state_stability"),
        (StClairOptions(line_length_start_mi=20, line_length_stop_mi=20), "thermal_ampacity"),
    ],
    ids=["voltage", "stability", "thermal"],
)
def test_curve_reports_voltage_stability_and_thermal_limits(
    options: StClairOptions, limit: str
) -> None:
    source = _input(conductor_ampacity_a=1 if limit == "thermal_ampacity" else 1e9)
    result = calculate_st_clair(source, options=options)
    assert result.curves[0].limit_type[0] == limit
