St. Clair loadability
=====================

Scope and inputs
----------------

The St. Clair implementation is a balanced, positive-sequence, steady-state
three-mesh calculation. It is not a transient-stability, fault, or mutual
multi-circuit coupling model. A line-level call uses each circuit's
``r1``, ``x1``, and ``b1`` values, conductor ampacity, bundle count, and
nominal line-to-line voltage. It returns one compact curve per circuit and
attaches the result to a copied line's ``ElectricalParameters``.

Direct input uses ``nominal_voltage_kv``, ``r_ohm_per_mile``,
``x_ohm_per_mile``, either ``b_siemens_per_mile`` or
``b_microsiemens_per_mile``, and ``conductor_ampacity_a`` (or ``ampacity_a``).
The facade ``calculate_st_clair_curve`` accepts a ``TransmissionLine`` or one
mapping; the lower-level ``calculations.st_clair.calculate_st_clair`` also
accepts a sequence of circuit mappings. Electrical results persist ``b1`` in
microsiemens/mile, converted to siemens/mile at the St. Clair boundary.

.. mermaid::
   :name: st-clair-loadability-search
   :alt: St. Clair solver searches each line length and angle for the first voltage, ampacity, or stability boundary
   :caption: St. Clair loadability search

   flowchart TD
     Inputs[Positive-sequence constants and options] --> Resolve[Resolve units and circuit ampacity]
     Resolve --> Length[Start next line length]
     Length --> Scale[Scale line constants and apply compensation]
     Scale --> Pi[Convert nominal pi to equivalent pi]
     Pi --> Angle[Try next sending-source angle]
     Angle --> Mesh[Solve three-mesh phasors]
     Mesh --> Valid{Mesh solution valid}
     Valid -->|no| Invalid[Record numerically invalid point]
     Valid -->|yes| Voltage{Voltage limit reached}
     Voltage -->|yes| VoltageRefine[Refine first voltage crossing]
     Voltage -->|no| Current{Ampacity limit reached}
     Current -->|yes| CurrentRefine[Refine first current crossing]
     Current -->|no| Stability{Stability angle reached}
     Stability -->|yes| Stable[Accept stability boundary]
     Stability -->|no| Angle
     VoltageRefine --> Store[Store boundary in curve arrays]
     CurrentRefine --> Store
     Stable --> Store
     Invalid --> Store
     Store --> More{More lengths}
     More -->|yes| Length
     More -->|no| Curves[Return base and sensitivity curves]

Defaults and units
------------------

Source voltage magnitudes default to 1.0 times nominal line-to-line voltage.
The sending and receiving Thevenin impedances default independently to
``0.1 + j1 ohm``. Shunt and series compensation default to zero;
``n_series_percent > 0`` reduces inductive line reactance. The receiving
voltage threshold defaults to 0.95 pu, the stability angle limit to 45 degrees,
and the search grid to 20--600 miles in 1-mile steps with 0.5-degree angle
steps. System impedances are ohms, line constants are ohm/mile and S/mile,
ampacity is amperes, and angle values are degrees at the public boundary.
No MVA base or per-unit impedance conversion is used.

At each length, the implementation scales series ``R`` and ``X`` by length and
total shunt ``B`` by length. It splits nominal shunt susceptance into sending
and receiving halves, applies the two shunt compensation settings separately,
and extracts equivalent asymmetric-pi values from the section's ABCD
parameters:

.. math::

   \begin{aligned}
   A &= 1 + ZY_r, \qquad B=Z, \qquad D=1+ZY_s, \\
   Z_{eq} &= B, \qquad Y_{s,eq}=\frac{D-1}{B},
   \qquad Y_{r,eq}=\frac{A-1}{B}.
   \end{aligned}

Three-mesh phasors
------------------

The source phasors and Thevenin branch impedances are used to solve the
three-mesh system. ``E1`` and ``E2`` are user-facing line-to-line quantities;
the balanced solver divides their magnitudes by ``sqrt(3)`` and uses the
receiving source as the zero-angle reference. ``I2`` is the line-series phase
current from sending to receiving end.

.. math::

    \begin{aligned}
    Z_1 &= R_1+jX_1, \qquad Z_2=R_2+jX_2, \\
    \begin{bmatrix}
       Z_1+Z_s & -Z_s & 0 \\
       -Z_s & Z_s+Z_\ell+Z_r & -Z_r \\
       0 & -Z_r & Z_2+Z_r
    \end{bmatrix}
    \begin{bmatrix}I_1\\I_2\\I_3\end{bmatrix}
    &= \begin{bmatrix}E_1\\0\\-E_2\end{bmatrix}, \\
    E_s &= E_1-Z_1I_1, \qquad E_r=E_2+Z_2I_3.
    \end{aligned}

The solver uses ``numpy.linalg.solve`` and rejects ill-conditioned or singular
mesh systems. Terminal phasors stored in the result are phase volts; reported
terminal voltage magnitudes are converted back to line-to-line volts.
Three-phase line-terminal powers and line loss are:

.. math::

   \begin{aligned}
   P_s &= 3\,\Re(E_s I_2^*), \qquad
   P_r = 3\,\Re(E_r I_2^*), \\
   P_{loss} &= P_s-P_r.
   \end{aligned}

Limits and output
-----------------

For each length, the code scans sending-source angle from zero through the
configured stability limit, always evaluating the exact final angle. It keeps
the first voltage or current boundary encountered; voltage and thermal
crossings are refined with 18 bisection steps. The configured stability angle
itself is the stability boundary and is not interpolated. Voltage equality is
tested against ``receiving_voltage_limit_pu * V_nominal``; current equality is
tested against conductor ampacity times subconductor count. Limit labels are
``voltage_drop``, ``thermal_ampacity``, ``steady_state_stability``, and
``numerically_invalid``.

Each ``StClairCurve`` stores parallel arrays for length, sending and receiving
power, loss, terminal voltage magnitudes and pu values, current, limiting
angle, limit type, and the real/imaginary components of relevant phasors. It
also stores the circuit's total nominal ampacity and its nominal-voltage
thermal reference:

.. math::

   \begin{aligned}
   I_{limit} &= I_{conductor}\,n_{subconductors}, \\
   P_{thermal,MW} &= \frac{\sqrt{3}V_{LL,V}I_{limit}}{10^6}.
   \end{aligned}

The thermal power is a reference value; the solver identifies the thermal
boundary by the phase-current threshold. Sensitivities form a Cartesian
product of supplied option values and are returned separately from the base
curves. The implementation and its tested constraints are in
``calculations/st_clair.py``, ``models/st_clair.py``, and
``test/calculations/test_st_clair.py``.

Notation and units
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 38 42

   * - Symbol
     - Meaning
     - Unit or convention
   * - ``R``, ``X``
     - Positive-sequence line resistance and reactance per mile
     - ohm/mile
   * - ``B``
     - Positive-sequence shunt susceptance per mile
     - S/mile internally; electrical result is microS/mile
   * - ``L``
     - Trial line length
     - mile
   * - ``Z_1``, ``Z_2``
     - Sending/receiving Thevenin impedances
     - ohm
   * - ``E_1``, ``E_2``
     - Source voltage magnitudes before phase conversion
     - V line-to-line
   * - ``E_s``, ``E_r``
     - Sending/receiving line-terminal phasors
     - phase V internally
   * - ``I_2``
     - Line series current
     - A per phase
   * - ``P_s``, ``P_r``, ``P_loss``
     - Three-phase real power and loss
     - W; parallel MW arrays are also stored
   * - ``N_series``, ``N_s``, ``N_r``
     - Series, sending-shunt, receiving-shunt compensation
     - percent
   * - ``theta_1``
     - Sending-source angle
     - degrees at API and in curve arrays
   * - ``I_limit``
     - Circuit current limit after bundle scaling
     - A
   * - ``P_thermal``
     - Nominal-voltage thermal power reference
     - MW

The older planning proposal called for natural-unit inputs and a compact
positive-sequence model; current code agrees, but its facade overload is
narrower than the proposed examples: ``transmissionlines.api.calculate_st_clair_curve``
accepts one mapping or one completed line, while the lower-level
``calculate_st_clair`` accepts a sequence of mappings for multiple circuits.
The line-level facade builds that sequence internally from per-circuit
``ElectricalParameters.circuit_scalars``. The older reference text also uses
some generic line-end power identities; this page states the line-terminal
phasor and current products actually evaluated by ``_solve_mesh``.