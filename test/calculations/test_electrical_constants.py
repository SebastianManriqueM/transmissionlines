"""Derive each electrical coefficient from physical constants, not from the code."""

from math import log, pi

import pytest

from transmissionlines.electrical_constants import (
    CAPACITIVE_REACTANCE_COEFFICIENT, EPSILON_AIR, KILOFEET_PER_MILE, L_C, L_F, R_C,
)

MU_0 = 4 * pi * 1e-7  # H/m
EPSILON_0 = 8.8541878128e-12  # F/m
MILE_M = 1609.344


def test_coefficients_match_first_principles() -> None:
    assert KILOFEET_PER_MILE == 5280 / 1000
    assert L_C == pytest.approx(MU_0 * MILE_M, rel=1e-5)  # f * mu0 per metre of ln(1/D)
    assert R_C == pytest.approx(pi**2 * 1e-7 * MILE_M, rel=1e-5)  # Carson: mu0 * omega / 8
    assert L_F == pytest.approx(2 * (-0.0386 + 0.5 * log(2 / 8.565e-4)), abs=2e-4)
    assert EPSILON_AIR == pytest.approx(EPSILON_0 * MILE_M * 1e6, rel=1e-3)  # uF/mile
    # 1.7788... published to four significant figures as 1.779
    assert CAPACITIVE_REACTANCE_COEFFICIENT == pytest.approx(1 / (4 * pi**2 * EPSILON_AIR), rel=2e-4)
