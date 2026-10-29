"""Pure natural-unit St. Clair loadability calculations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import itertools
from math import sqrt
from typing import Any

import numpy as np

from transmissionlines.calculations.constants import (
    ST_CLAIR_BOUNDARY_REFINEMENT_STEPS,
    ST_CLAIR_LENGTH_GRID_STOP_PADDING_STEPS,
    ST_CLAIR_MAX_MESH_CONDITION_NUMBER,
    ST_CLAIR_MIN_SERIES_IMPEDANCE_OHM,
    ST_CLAIR_MIN_SERIES_REACTANCE_OHM,
)
from transmissionlines.models.st_clair import (
    StClairCurve,
    StClairLineConstants,
    StClairOptions,
    StClairResult,
)


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
        conductor_family=values.get("conductor_family"),
        conductor_codeword=values.get("conductor_codeword"),
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
    r"""Convert nominal-pi parameters to the pi network with the same ABCD matrix.

    For a nominal pi, :math:`A = 1 + Z Y_r`, :math:`B = Z`, :math:`D = 1 + Z Y_s`, and

    .. math:: Z' = B = Z, \qquad Y'_s = \frac{D - 1}{B} = Y_s, \qquad Y'_r = \frac{A - 1}{B} = Y_r,

    so the result equals the input up to rounding. It does **not** apply the
    distributed-parameter (long-line) correction
    :math:`Z' = Z \frac{\sinh \gamma\ell}{\gamma\ell}`,
    :math:`Y'/2 = \frac{Y}{2} \frac{\tanh(\gamma\ell/2)}{\gamma\ell/2}`.

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
    if abs(b) < ST_CLAIR_MIN_SERIES_IMPEDANCE_OHM:
        raise ValueError("nominal-pi series impedance is too small for equivalent-pi conversion")
    z_equivalent = b
    y_s_equivalent = (d - 1) / b
    y_r_equivalent = (a - 1) / b
    return z_equivalent, y_s_equivalent, y_r_equivalent


def _solve_mesh(
    constants: StClairLineConstants, options: StClairOptions, length_mi: float, angle_deg: float | np.ndarray
) -> dict[str, Any]:
    r"""Solve the balanced three-mesh circuit at one line length for one or more angles.

    Per phase, a sending source :math:`E_1 = |E_1| e^{j\delta}` behind :math:`Z_1` and a
    receiving source :math:`E_2` behind :math:`Z_2` connect through the line's pi
    (shunt impedances :math:`Z_{s,r} = 1/Y_{s,r}`, series :math:`Z`). Kirchhoff's
    voltage law around the three meshes gives

    .. math::
        \begin{bmatrix} Z_1 + Z_s & -Z_s & 0 \\ -Z_s & Z_s + Z + Z_r & -Z_r \\ 0 & -Z_r & Z_2 + Z_r \end{bmatrix}
        \begin{bmatrix} I_1 \\ I_2 \\ I_3 \end{bmatrix}
        = \begin{bmatrix} E_1 \\ 0 \\ -E_2 \end{bmatrix},

    with terminal voltages :math:`E_s = E_1 - Z_1 I_1`, :math:`E_r = E_2 + Z_2 I_3`, and
    three-phase power :math:`P = 3\,\mathrm{Re}(V I_2^*)` at each terminal (the shunt
    branches are lossless, so :math:`I_2` carries all the real power). The matrix
    depends only on the line length; :math:`\delta` enters only through :math:`E_1`, so
    all angles share one solve, and results have the shape of ``angle_deg``.
    """
    r = constants.r_ohm_per_mile * length_mi
    x = constants.x_ohm_per_mile * length_mi * (1 - options.n_series_percent / 100)
    if abs(x) < ST_CLAIR_MIN_SERIES_REACTANCE_OHM and not options.allow_near_zero_series_reactance:
        raise ValueError("series compensation produces near-zero series reactance")
    z_line = complex(r, x)
    b_total = constants.b_siemens_per_mile * length_mi
    y_s_nom = 1j * b_total / 2 * (1 - options.n_s_percent / 100)
    y_r_nom = 1j * b_total / 2 * (1 - options.n_r_percent / 100)
    # Known limitation, likely inherited from the Julia original: this is the nominal pi at
    # every length, with no distributed-parameter correction. For a 230 kV Cardinal circuit
    # the exact long-line pi has Z' = Z sinh(gl)/gl about 0.94 Z at 300 mi and 0.76 Z at
    # 600 mi, and Y' about 1.03 Y and 1.15 Y, so curves past ~200 mi overstate series
    # impedance. Fix: scale Z and Y by those factors, with gamma = sqrt(z * y) per mile.
    z_line, y_s, y_r = nominal_pi_to_equivalent_pi(z_line, y_s_nom, y_r_nom)
    z_s, z_r = 1 / y_s, 1 / y_r
    z_1 = complex(options.r_system_1_ohm, options.x_system_1_ohm)
    z_2 = complex(options.r_system_2_ohm, options.x_system_2_ohm)
    angle = np.asarray(angle_deg, dtype=float)
    e1 = (constants.e1_v / sqrt(3)) * np.exp(1j * np.deg2rad(angle))
    e2 = constants.e2_v / sqrt(3)
    matrix = np.array(
        [[z_1 + z_s, -z_s, 0], [-z_s, z_s + z_line + z_r, -z_r], [0, -z_r, z_2 + z_r]],
        dtype=complex,
    )
    if np.linalg.cond(matrix) > ST_CLAIR_MAX_MESH_CONDITION_NUMBER:
        raise ValueError("three-mesh system is ill-conditioned")
    rhs = np.stack([e1.ravel(), np.zeros(e1.size), np.full(e1.size, -e2)])
    try:
        i1, i2, i3 = (row.reshape(angle.shape) for row in np.linalg.solve(matrix, rhs))
    except np.linalg.LinAlgError as error:
        raise ValueError("three-mesh system is singular") from error
    es = e1 - z_1 * i1
    er = e2 + z_2 * i3
    ps = 3 * np.real(es * np.conjugate(i2))
    pr = 3 * np.real(er * np.conjugate(i2))
    return {
        "es": es, "er": er, "i1": i1, "i2": i2, "i3": i3, "e1": e1, "e2": e2,
        "z_s": z_s, "z_r": z_r, "z_line": z_line, "ps_w": ps, "pr_w": pr, "loss_w": ps - pr,
        "series_loss_w": 3 * r * np.abs(i2) ** 2,
    }


def _first_limit(
    constants: StClairLineConstants, options: StClairOptions, length_mi: float, angles: np.ndarray,
    voltage_limit: float, ampacity: float,
) -> tuple[tuple[complex, complex, complex], float, str]:
    """Return (Es, Er, I2) where the first limit binds along the angle sweep, its angle, and its type.

    The stability limit is the last angle itself. A voltage or thermal crossing is
    refined by bisection between the last passing angle and the first failing one.
    """
    try:
        sweep = _solve_mesh(constants, options, length_mi, angles)
    except ValueError:
        return (0j, 0j, 0j), 0.0, "numerically_invalid"
    voltage_hit = np.abs(sweep["er"]) <= voltage_limit
    hits = np.flatnonzero(voltage_hit | (np.abs(sweep["i2"]) >= ampacity))
    if not hits.size:
        return (sweep["es"][-1], sweep["er"][-1], sweep["i2"][-1]), float(angles[-1]), "steady_state_stability"
    k = hits[0]
    kind = "voltage_drop" if voltage_hit[k] else "thermal_ampacity"
    point = (sweep["es"][k], sweep["er"][k], sweep["i2"][k])
    lower, upper = (float(angles[k - 1]) if k else 0.0), float(angles[k])
    for _ in range(ST_CLAIR_BOUNDARY_REFINEMENT_STEPS):
        midpoint = (lower + upper) / 2
        candidate = _solve_mesh(constants, options, length_mi, midpoint)
        hit = (abs(candidate["er"]) <= voltage_limit if kind == "voltage_drop"
               else abs(candidate["i2"]) >= ampacity)
        if hit:
            upper, point = midpoint, (candidate["es"], candidate["er"], candidate["i2"])
        else:
            lower = midpoint
    return point, upper, kind


def _make_curve(
    constants: StClairLineConstants, options: StClairOptions, *, name: str
) -> StClairCurve:
    """Calculate the first loadability boundary for each line length.

    The exact configured stability-angle endpoint is always evaluated, even
    when ``angle_step_deg`` does not divide it evenly. Unlike voltage and
    thermal thresholds, the stability boundary is the configured policy limit
    itself and is not interpolated from a neighboring angle sample.
    """
    lengths = np.arange(
        options.line_length_start_mi,
        options.line_length_stop_mi + options.line_length_step_mi * ST_CLAIR_LENGTH_GRID_STOP_PADDING_STEPS,
        options.line_length_step_mi,
    )
    angles = np.append(np.arange(0.0, options.stability_angle_limit_deg, options.angle_step_deg),
                       options.stability_angle_limit_deg)
    ampacity = constants.conductor_ampacity_a * constants.subconductor_count
    voltage_limit = constants.nominal_voltage_v * options.receiving_voltage_limit_pu / sqrt(3)
    limits = [_first_limit(constants, options, float(length), angles, voltage_limit, ampacity) for length in lengths]
    es, er, i2 = (np.array([point[index] for point, _, _ in limits], dtype=complex) for index in range(3))
    ps = 3 * np.real(es * np.conjugate(i2))
    pr = 3 * np.real(er * np.conjugate(i2))
    return StClairCurve(
        name=name,
        circuit_id=constants.circuit_id,
        lengths_mi=lengths.tolist(),
        pr_w=pr.tolist(),
        pr_mw=(pr / 1e6).tolist(),
        ps_w=ps.tolist(),
        ps_mw=(ps / 1e6).tolist(),
        loss_w=(ps - pr).tolist(),
        abs_es_volt=(np.abs(es) * sqrt(3)).tolist(),
        abs_er_volt=(np.abs(er) * sqrt(3)).tolist(),
        abs_er_pu=(np.abs(er) * sqrt(3) / constants.nominal_voltage_v).tolist(),
        current_a=np.abs(i2).tolist(),
        limiting_angle_deg=[angle for _, angle, _ in limits],
        limit_type=[kind for _, _, kind in limits],
        es_real_volt=es.real.tolist(),
        es_imag_volt=es.imag.tolist(),
        er_real_volt=er.real.tolist(),
        er_imag_volt=er.imag.tolist(),
        i2_real_a=i2.real.tolist(),
        i2_imag_a=i2.imag.tolist(),
        circuit_nominal_ampacity_a=ampacity,
        thermal_power_mw=sqrt(3) * constants.nominal_voltage_v * ampacity / 1e6,
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


__all__ = [
    "calculate_st_clair",
    "nominal_pi_to_equivalent_pi",
]