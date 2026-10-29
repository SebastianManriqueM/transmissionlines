"""Check each formula against its familiar textbook form, written independently of the code."""

from math import cosh, log, pi, sin

import numpy as np
import pytest

from transmissionlines.bundle import bundle_gmr, regular_polygon_coordinates
from transmissionlines.calculations.cable import solid_round_wire_gmr
from transmissionlines.calculations.electrical import build_primitive_p, build_primitive_z
from transmissionlines.calculations.matrices import fully_transpose, sequence_matrix
from transmissionlines.calculations.sag import solve_span_sag
from transmissionlines.models.geometry import CablePosition

POSITIONS = [CablePosition(x_ft=0, y_ft=30), CablePosition(x_ft=4, y_ft=40)]


def test_carson_impedance_at_60_hz_and_100_ohm_m() -> None:
    # Kersting: z_ii = r + 0.09530 + j0.12134 (ln 1/GMR + 7.93402), z_ij with D_ij in place of GMR
    z = build_primitive_z(POSITIONS, gmrs=[0.03, 0.03], resistances=[0.1, 0.1], bundle_counts=[1, 1],
                          frequency=60, earth_resistivity=100)
    assert z[0, 0] == pytest.approx(0.1 * 5.28 + 0.09530 + 0.12134j * (log(1 / 0.03) + 7.93402), rel=1e-4)
    assert z[0, 1] == pytest.approx(0.09530 + 0.12134j * (log(1 / np.hypot(4, 10)) + 7.93402), rel=1e-4)


def test_potential_coefficients_by_method_of_images() -> None:
    # P_ii = 11.17689 ln(2h / r), P_ij = 11.17689 ln(S_ij / D_ij), in mile/uF
    p = build_primitive_p(POSITIONS, radii=[0.05, 0.05])
    assert p[0, 0] == pytest.approx(11.17689 * log(60 / 0.05), rel=1e-4)
    assert p[0, 1] == pytest.approx(11.17689 * log(np.hypot(4, 70) / np.hypot(4, 10)), rel=1e-4)


def test_symmetrical_components_of_a_transposed_line() -> None:
    zs, zm = 0.5 + 1.2j, 0.1 + 0.5j
    z = fully_transpose(np.full((3, 3), zm) + np.eye(3) * (zs - zm) + np.diag([0.01, -0.02, 0.01]))
    z012 = sequence_matrix(z)
    assert np.allclose(z012, np.diag([zs + 2 * zm, zs - zm, zs - zm]))


def test_solid_wire_and_bundle_geometry() -> None:
    assert solid_round_wire_gmr(1.2) == pytest.approx(0.7788 * 0.6 / 12, rel=1e-4)
    xy = regular_polygon_coordinates(4, 18)
    assert np.hypot(*xy.T) == pytest.approx(18 / (2 * sin(pi / 4)))  # circumradius s / (2 sin(pi/n))
    # 4-bundle: (GMR * s * s * s*sqrt(2))^(1/4), with s in feet
    s = 18 / 12
    assert bundle_gmr(0.03, 4, 18) == pytest.approx((0.03 * s * s * s * 2**0.5) ** 0.25)


def test_level_span_sag_is_the_catenary_sag() -> None:
    # At the reference state the tension is the reference tension, so D = c (cosh(S/2c) - 1)
    weight, strength, span = 1.094, 31_500, 1000
    sag, position, tension = solve_span_sag(
        weight, strength, area_in2=0.7264, modulus_psi=11.5e6, expansion_per_c=19.3e-6,
        reference_fraction=0.2, span_ft=span, rise_ft=0,
        reference_temperature_c=25, operating_temperature_c=25,
    )
    c = 0.2 * strength / weight
    assert tension == pytest.approx(0.2 * strength)
    assert position == pytest.approx(span / 2)
    assert sag == pytest.approx(c * (cosh(span / (2 * c)) - 1))
    assert sag == pytest.approx(weight * span**2 / (8 * tension), rel=1e-3)  # parabolic approximation


def test_hotter_conductor_sags_more() -> None:
    common = dict(area_in2=0.7264, modulus_psi=11.5e6, expansion_per_c=19.3e-6, reference_fraction=0.2,
                  span_ft=1000, rise_ft=0, reference_temperature_c=25)
    cold, _, _ = solve_span_sag(1.094, 31_500, operating_temperature_c=25, **common)
    hot, _, _ = solve_span_sag(1.094, 31_500, operating_temperature_c=100, **common)
    assert hot > cold
