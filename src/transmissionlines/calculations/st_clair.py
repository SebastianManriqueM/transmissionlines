"""Pure natural-unit St. Clair loadability calculations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import itertools
from math import sqrt
from typing import Any

import numpy as np

from transmissionlines.models.st_clair import (
    StClairCurve,
    StClairLineConstants,
    StClairOptions,
    StClairResult,
)
from transmissionlines.models.parameters import LineParameters


def _resolve_constants(
    values: Mapping[str, Any], options: StClairOptions, *, circuit_id: str
) -> StClairLineConstants:
    """Resolve a direct-input circuit mapping into validated natural units."""
    voltage = float(values["nominal_voltage_kv"]) * 1000.0
    b_value = float(values.get("b_siemens_per_mile", float(values.get("b_microsiemens_per_mile", 0)) * 1e-6))
    ampacity = values.get("conductor_ampacity_a", values.get("ampacity_a"))
    if ampacity is None:
        raise ValueError("conductor_ampacity_a is required to calculate the thermal limit")
    return StClairLineConstants(
        circuit_id=circuit_id,
        r_ohm_per_mile=float(values["r_ohm_per_mile"]),
        x_ohm_per_mile=float(values["x_ohm_per_mile"]),
        b_siemens_per_mile=b_value,
        nominal_voltage_v=voltage,
        e1_v=options.abs_e1_pu * voltage,
        e2_v=options.abs_e2_pu * voltage,
        conductor_ampacity_a=float(ampacity),
        subconductor_count=int(values.get("subconductor_count", 1)),
        source_scalars=dict(values.get("source_scalars", {"r": "r1", "x": "x1", "b": "b1"})),
    )


def nominal_pi_to_equivalent_pi(
    z_ohm: complex,
    y_s_siemens: complex,
    y_r_siemens: complex,
) -> tuple[complex, complex, complex]:
    """Extract an exact asymmetric pi from its ABCD two-port matrix.

    Parameters
    ----------
    z_ohm : complex
        Series impedance of the nominal pi section.
    y_s_siemens, y_r_siemens : complex
        Sending- and receiving-end nominal shunt admittances.

    Returns
    -------
    tuple of complex
        Equivalent series impedance, sending shunt, and receiving shunt.
    """
    a = 1 + z_ohm * y_r_siemens
    b = z_ohm
    d = 1 + z_ohm * y_s_siemens
    if abs(b) < 1e-15:
        raise ValueError("nominal-pi series impedance is too small for equivalent-pi conversion")
    z_equivalent = b
    y_s_equivalent = (d - 1) / b
    y_r_equivalent = (a - 1) / b
    return z_equivalent, y_s_equivalent, y_r_equivalent


def _solve_mesh(
    constants: StClairLineConstants, options: StClairOptions, length_mi: float, angle_deg: float
) -> dict[str, complex | float]:
    """Solve one balanced phase-domain mesh point; angles enter in degrees."""
    r = constants.r_ohm_per_mile * length_mi
    x = constants.x_ohm_per_mile * length_mi * (1 - options.n_series_percent / 100)
    if abs(x) < 1e-12 and not options.allow_near_zero_series_reactance:
        raise ValueError("series compensation produces near-zero series reactance")
    z_line = complex(r, x)
    b_total = constants.b_siemens_per_mile * length_mi
    y_s_nom = 1j * b_total / 2 * (1 - options.n_s_percent / 100)
    y_r_nom = 1j * b_total / 2 * (1 - options.n_r_percent / 100)
    z_line, y_s, y_r = nominal_pi_to_equivalent_pi(z_line, y_s_nom, y_r_nom)
    z_s, z_r = 1 / y_s, 1 / y_r
    z_1 = complex(options.r_system_1_ohm, options.x_system_1_ohm)
    z_2 = complex(options.r_system_2_ohm, options.x_system_2_ohm)
    e1 = (constants.e1_v / sqrt(3)) * np.exp(1j * np.deg2rad(angle_deg))
    e2 = constants.e2_v / sqrt(3)
    matrix = np.array(
        [[z_1 + z_s, -z_s, 0], [-z_s, z_s + z_line + z_r, -z_r], [0, -z_r, z_2 + z_r]],
        dtype=complex,
    )
    if np.linalg.cond(matrix) > 1e14:
        raise ValueError("three-mesh system is ill-conditioned")
    try:
        i1, i2, i3 = np.linalg.solve(matrix, np.array([e1, 0, -e2], dtype=complex))
    except np.linalg.LinAlgError as error:
        raise ValueError("three-mesh system is singular") from error
    es = e1 - z_1 * i1
    er = e2 + z_2 * i3
    ps = 3 * float(np.real(es * np.conjugate(i2)))
    pr = 3 * float(np.real(er * np.conjugate(i2)))
    loss = ps - pr
    return {
        "es": es,
        "er": er,
        "i2": i2,
        "i1": i1,
        "i3": i3,
        "e1": e1,
        "e2": e2,
        "z_s": z_s,
        "z_r": z_r,
        "ps_w": ps,
        "pr_w": pr,
        "loss_w": loss,
        "series_loss_w": 3 * r * abs(i2) ** 2,
        "z_line": z_line,
    }


def _make_curve(
    constants: StClairLineConstants, options: StClairOptions, *, name: str
) -> StClairCurve:
    """Calculate and compact the first loadability boundary for each length.

    The exact configured stability-angle endpoint is always evaluated, even
    when ``angle_step_deg`` does not divide it evenly. Unlike voltage and
    thermal thresholds, the stability boundary is the configured policy limit
    itself and is not interpolated from a neighboring angle sample.
    """
    lengths = np.arange(
        options.line_length_start_mi,
        options.line_length_stop_mi + options.line_length_step_mi * 0.5,
        options.line_length_step_mi,
    )
    angles = np.arange(0.0, options.stability_angle_limit_deg, options.angle_step_deg)
    angles = np.append(angles, options.stability_angle_limit_deg)
    ampacity = constants.conductor_ampacity_a * constants.subconductor_count
    thermal_mw = sqrt(3) * constants.nominal_voltage_v * ampacity / 1e6
    data: dict[str, list[Any]] = {key: [] for key in (
        "pr_w", "ps_w", "loss_w", "abs_es_volt", "abs_er_volt", "abs_er_pu", "current_a",
        "limiting_angle_deg", "limit_type", "es_real_volt", "es_imag_volt", "er_real_volt",
        "er_imag_volt", "i2_real_a", "i2_imag_a",
    )}
    voltage_limit = constants.nominal_voltage_v * options.receiving_voltage_limit_pu / sqrt(3)
    for length in lengths:
        boundary = None
        boundary_type = "steady_state_stability"
        previous_angle = 0.0
        for angle in angles:
            try:
                point = _solve_mesh(constants, options, float(length), float(angle))
            except ValueError:
                boundary_type = "numerically_invalid"
                break
            current = abs(point["i2"])
            if abs(point["er"]) <= voltage_limit:
                boundary, boundary_type = point, "voltage_drop"
            elif current >= ampacity:
                boundary, boundary_type = point, "thermal_ampacity"
            else:
                boundary = point
                previous_angle = float(angle)
                if angle >= options.stability_angle_limit_deg:
                    boundary_type = "steady_state_stability"
                    break
                continue
            if boundary is not None:
                lower, upper = previous_angle, float(angle)
                for _ in range(18):
                    midpoint = (lower + upper) / 2
                    candidate = _solve_mesh(constants, options, float(length), midpoint)
                    hit_limit = (
                        abs(candidate["er"]) <= voltage_limit
                        if boundary_type == "voltage_drop"
                        else abs(candidate["i2"]) >= ampacity
                    )
                    if hit_limit:
                        upper, boundary = midpoint, candidate
                    else:
                        lower = midpoint
                angle = upper
                break
        if boundary is None:
            data["pr_w"].append(0.0)
            data["ps_w"].append(0.0)
            data["loss_w"].append(0.0)
            data["abs_es_volt"].append(0.0)
            data["abs_er_volt"].append(0.0)
            data["abs_er_pu"].append(0.0)
            data["current_a"].append(0.0)
            data["limiting_angle_deg"].append(float(previous_angle))
            data["limit_type"].append("numerically_invalid")
            for field in ("es_real_volt", "es_imag_volt", "er_real_volt", "er_imag_volt", "i2_real_a", "i2_imag_a"):
                data[field].append(0.0)
            continue
        es, er, i2 = boundary["es"], boundary["er"], boundary["i2"]
        data["pr_w"].append(boundary["pr_w"])
        data["ps_w"].append(boundary["ps_w"])
        data["loss_w"].append(boundary["loss_w"])
        data["abs_es_volt"].append(abs(es) * sqrt(3))
        data["abs_er_volt"].append(abs(er) * sqrt(3))
        data["abs_er_pu"].append(abs(er) * sqrt(3) / constants.nominal_voltage_v)
        data["current_a"].append(abs(i2))
        data["limiting_angle_deg"].append(float(angle))
        data["limit_type"].append(boundary_type)
        data["es_real_volt"].append(float(es.real))
        data["es_imag_volt"].append(float(es.imag))
        data["er_real_volt"].append(float(er.real))
        data["er_imag_volt"].append(float(er.imag))
        data["i2_real_a"].append(float(i2.real))
        data["i2_imag_a"].append(float(i2.imag))
    return StClairCurve(
        name=name,
        circuit_id=constants.circuit_id,
        lengths_mi=lengths[: len(data["pr_w"])].tolist(),
        pr_w=data["pr_w"],
        pr_mw=[value / 1e6 for value in data["pr_w"]],
        ps_w=data["ps_w"],
        ps_mw=[value / 1e6 for value in data["ps_w"]],
        loss_w=data["loss_w"],
        abs_es_volt=data["abs_es_volt"],
        abs_er_volt=data["abs_er_volt"],
        abs_er_pu=data["abs_er_pu"],
        current_a=data["current_a"],
        limiting_angle_deg=data["limiting_angle_deg"],
        limit_type=data["limit_type"],
        es_real_volt=data["es_real_volt"],
        es_imag_volt=data["es_imag_volt"],
        er_real_volt=data["er_real_volt"],
        er_imag_volt=data["er_imag_volt"],
        i2_real_a=data["i2_real_a"],
        i2_imag_a=data["i2_imag_a"],
        circuit_nominal_ampacity_a=ampacity,
        thermal_power_mw=thermal_mw,
    )


def calculate_st_clair(
    positive_sequence: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    options: StClairOptions | None = None,
    sensitivities: Mapping[str, Sequence[float]] | None = None,
) -> StClairResult:
    """Calculate one or more St. Clair curves from explicit natural-unit inputs.

    Parameters
    ----------
    positive_sequence : mapping or sequence of mappings
        Each mapping supplies ``nominal_voltage_kv``, ``r_ohm_per_mile``,
        ``x_ohm_per_mile`` and ``b_siemens_per_mile`` (or
        ``b_microsiemens_per_mile``), plus optional ampacity/bundle metadata.
    options : StClairOptions, optional
        Search and operating limits. Defaults follow the public plan.
    sensitivities : mapping, optional
        Option names mapped to sampled values. The Cartesian family is
        recalculated independently while retaining the base curves.

    Returns
    -------
    StClairResult
        JSON-safe compact arrays for each circuit and sensitivity scenario.
    """
    active_options = options or StClairOptions()
    input_values = [positive_sequence] if isinstance(positive_sequence, Mapping) else list(positive_sequence)
    if not input_values:
        raise ValueError("at least one positive-sequence circuit is required")
    constants = [
        _resolve_constants(item, active_options, circuit_id=str(item.get("circuit_id", f"circuit-{index + 1}")))
        for index, item in enumerate(input_values)
    ]
    base = [_make_curve(item, active_options, name="base") for item in constants]
    sensitivity_curves: list[StClairCurve] = []
    if sensitivities:
        names, values = zip(*sensitivities.items(), strict=True)
        for scenario_values in itertools.product(*values):
            updates = dict(zip(names, scenario_values, strict=True))
            scenario = StClairOptions.model_validate({**active_options.model_dump(), **updates})
            scenario_name = ", ".join(f"{key}={value:g}" for key, value in updates.items())
            scenario_constants = [
                item.model_copy(update={
                    "e1_v": scenario.abs_e1_pu * item.nominal_voltage_v,
                    "e2_v": scenario.abs_e2_pu * item.nominal_voltage_v,
                })
                for item in constants
            ]
            sensitivity_curves.extend(
                _make_curve(item, scenario, name=scenario_name) for item in scenario_constants
            )
    return StClairResult(
        options=active_options,
        line_constants=constants,
        curves=base,
        sensitivity_curves=sensitivity_curves,
    )


def calculate_st_clair_curve_for_line(
    line: Any,
    *,
    options: StClairOptions | None = None,
    sensitivities: Mapping[str, Sequence[float]] | None = None,
) -> Any:
    """Return a copied line with curves resolved from its electrical result."""
    parameters = line.line_parameters
    electrical = None if parameters is None else parameters.electrical_parameters
    if electrical is None or electrical.status != "complete":
        raise ValueError("St. Clair calculation requires complete electrical parameters")
    if not electrical.circuit_scalars:
        raise ValueError("electrical result is missing per-circuit positive-sequence scalars")
    specifications = {spec.circuit_id: spec for spec in line.tower_configuration.phase_conductor_specs}
    voltage_kv = line.technical_info.nominal_voltage.to("kilovolt").magnitude
    inputs = []
    for circuit_id, scalars in electrical.circuit_scalars.items():
        missing = {"r1", "x1", "b1"} - scalars.keys()
        if missing:
            raise ValueError(f"{circuit_id} is missing positive-sequence scalars: {sorted(missing)}")
        spec = specifications.get(circuit_id)
        if spec is None or spec.conductor.ampacity is None:
            raise ValueError(f"missing conductor ampacity for {circuit_id}")
        inputs.append({
            "circuit_id": circuit_id,
            "nominal_voltage_kv": voltage_kv,
            "r_ohm_per_mile": scalars["r1"],
            "x_ohm_per_mile": scalars["x1"],
            "b_microsiemens_per_mile": scalars["b1"],
            "conductor_ampacity_a": spec.conductor.ampacity.to("ampere").magnitude,
            "subconductor_count": spec.subconductor_count,
        })
    curve_result = calculate_st_clair(
        inputs, options=options, sensitivities=sensitivities
    ).model_copy(update={"line_name": line.technical_info.line_name})
    updated_electrical = electrical.model_copy(update={"st_clair_curve": curve_result})
    updated_parameters = (parameters or LineParameters()).model_copy(
        update={"electrical_parameters": updated_electrical}
    )
    return line.model_copy(update={"line_parameters": updated_parameters})


__all__ = [
    "calculate_st_clair",
    "calculate_st_clair_curve_for_line",
    "nominal_pi_to_equivalent_pi",
]