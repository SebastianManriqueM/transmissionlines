r"""Coefficients of the modified Carson and potential-coefficient equations.

Lengths in the electrical formulas are feet and results are per mile; with
:math:`\mu_0 = 4\pi\times10^{-7}` H/m, :math:`\varepsilon_0 = 8.854\times10^{-12}` F/m,
and 1 mile = 1609.344 m:

* ``L_C`` :math:`= \mu_0 \cdot 1609.344` Ω/mile/Hz. The inductive reactance per
  unit length of :math:`\ln(1/D)` is :math:`\omega \mu_0 / 2\pi = f \mu_0`.
* ``R_C`` :math:`= \pi^2 \cdot 10^{-7} \cdot 1609.344` Ω/mile/Hz. Carson's
  earth-return resistance is :math:`\mu_0 \omega / 8 = \pi^2 f \cdot 10^{-7}` Ω/m.
* ``L_F`` :math:`= 2\left(-0.0386 + \tfrac12 \ln(2 / 8.565\times10^{-4})\right)`, the
  constant left when Carson's correction terms are truncated to their first terms
  (the "modified Carson" equations, as in Kersting). Together with
  :math:`\tfrac12 \ln(\rho/f)` it is :math:`\ln D_e` for the equivalent earth-return
  depth :math:`D_e \approx 2160\sqrt{\rho/f}` ft.
* ``EPSILON_AIR`` :math:`\approx \varepsilon_0 \cdot 1609.344 \cdot 10^{6}` µF/mile
  (the textbook value 1.4240e-2; the exact product is 1.4249e-2).
* ``CAPACITIVE_REACTANCE_COEFFICIENT`` :math:`= 1 / (4\pi^2\,\varepsilon)` MΩ·mile·Hz:
  the capacitive reactance of :math:`\ln(1/r)` is :math:`\frac{1}{2\pi f}\cdot\frac{1}{2\pi\varepsilon}`.
"""

KILOFEET_PER_MILE = 5.28
SERIES_REACTANCE_COEFFICIENT = 0.00202237
CAPACITIVE_REACTANCE_COEFFICIENT = 1.779
R_C = 0.00158836
L_C = SERIES_REACTANCE_COEFFICIENT
L_F = 7.6786
EPSILON_AIR = 1.4240e-2
