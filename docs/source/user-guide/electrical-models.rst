Electrical models and equations
===============================

The electrical calculation follows the implemented Julia-parity convention.
It orders phases by circuit and A/B/C, then ground wires by wire ID. Geometry,
conductor and ground-wire properties produce primitive series impedance
``Zabcg`` and primitive potential coefficients ``Pabcg``. Ground wires are
eliminated with Kron reduction; the reduced potential is converted to shunt
admittance. The engine returns non-transposed (``*_nt``), fully transposed
(``*_ft``), and symmetrical-component (``Z012``/``Y012``) results.

.. mermaid::
   :name: electrical-calculation-sequence
   :alt: Electrical inputs flow through primitive matrices, Kron reduction, transposition, sequence transforms, and result packaging
   :caption: Electrical calculation sequence

   flowchart TD
     Inputs[Validated geometry and cable specifications] --> Order[Order phases and ground wires]
     Order --> Primitive[Build primitive Z and P matrices]
     Primitive --> Kron[Reduce Z and P over ground wires]
     Kron --> Znt[Calculate non-transposed sequence Z]
     Kron --> PtoY[Convert reduced P to shunt Y]
     PtoY --> Ynt[Calculate non-transposed sequence Y]
     Kron --> Ztranspose[Transpose reduced Z by circuit]
     PtoY --> Ytranspose[Transpose reduced Y by circuit]
     Ztranspose --> Zsequence[Transform transposed Z to sequence coordinates]
     Ytranspose --> Ysequence[Transform transposed Y to sequence coordinates]
     Znt --> Package[Package matrices labels units and provenance]
     Ynt --> Package
     Zsequence --> Scalars[Extract sequence scalars and SIL]
     Ysequence --> Scalars
     Scalars --> Package

Primitive series impedance
---------------------------

For conductor index ``i``, the diagonal uses bundle GMR ``GMR_i`` and the
resistance of one subconductor divided by bundle count. For ``i != j``, the
mutual logarithm uses direct phase-to-phase distance ``d_ij``. The code uses
the same parity correction for diagonal and mutual terms:

.. math::

   \begin{aligned}
   C_f &= L_F + \frac{1}{2}\ln\left(\frac{\rho}{f}\right), \\
   Z_{ii} &= 5.28\frac{R_{ac,i}}{n_i} + R_C f
            + j L_C f\left[\ln\left(\frac{1}{\mathrm{GMR}_i}\right)+C_f\right], \\
   Z_{ij} &= R_C f
            + j L_C f\left[\ln\left(\frac{1}{d_{ij}}\right)+C_f\right],\quad i\ne j.
   \end{aligned}

Here ``R_ac`` is the selected phase AC resistance in ohm/kilofoot, ``n_i`` is
the phase subconductor count, ``f`` is frequency in hertz, and ``rho`` is earth
resistivity in ohm-meter. The parity constants are ``R_C = 0.00158836``,
``L_C = 0.00202237``, and ``L_F = 7.6786``. Distances and GMR are in feet;
``5.28`` converts the selected ohm/kilofoot conductor resistance to the
implementation's ohm/mile scale. Ground-wire diagonal resistance uses its
DC resistance and its unbundled GMR. The off-diagonal resistance contribution
is ``R_C f`` as implemented; it is not replaced with a more general earth-return
model.

Potential coefficients
----------------------

``S_ij`` is the distance to the image of conductor ``j`` reflected below the
ground plane. The diagonal uses the image distance and conductor equivalent
radius; mutual entries use both image and direct distances:

.. math::

   \begin{aligned}
   P_{ii} &= \frac{1}{2\pi\epsilon_{air}}
            \ln\left(\frac{S_{ii}}{r_i}\right), \\
   P_{ij} &= \frac{1}{2\pi\epsilon_{air}}
            \ln\left(\frac{S_{ij}}{d_{ij}}\right),\quad i\ne j,
   \qquad \epsilon_{air}=1.4240\times10^{-2}.
   \end{aligned}

``P`` is stored in the Julia parity unit contract ``1/(microSiemens/mile)``.
The Python ``build_primitive_p`` function retains a frequency argument for
interface compatibility but does not use it in this matrix.

Kron reduction and shunt admittance
-----------------------------------

Partition a primitive matrix into phase (``p``) and ground-wire (``g``) blocks.
The implementation uses a linear solve for the ground block in its Schur
complement:

.. math::

   M_{p,\mathrm{reduced}} = M_{pp} - M_{pg}M_{gg}^{-1}M_{gp}.

The reduced potential is converted to admittance using the frequency and
matrix-inversion convention below. The output unit is microsiemens per mile.

.. math::

   Y_{\mathrm{kron}} = j\,2\pi f\,P_{\mathrm{kron}}^{-1}.

Symmetrical components and transposition
-----------------------------------------

For each three-phase circuit the implementation uses ``a = exp(j 2 pi / 3)``
and the following phase-to-sequence transformation. Multi-circuit matrices use
one copy of ``T`` per circuit on the block diagonal.

.. math::

   \begin{aligned}
   T &= \begin{bmatrix}1&1&1\\1&a^2&a\\1&a&a^2\end{bmatrix}, \\
   M_{012} &= T^{-1}M_{abc}T.
   \end{aligned}

Rows and columns are labelled ``zero``, ``positive``, and ``negative``. Full
transposition is the code's matrix averaging operation, not a geometric
recalculation: within each circuit it averages the three self entries and the
six ordered off-diagonal entries separately. For multiple circuits, every
entry in each inter-circuit 3-by-3 block is replaced by that block's mean. The
non-transposed matrices carry the ``_nt`` suffix; their fully transposed forms
carry ``_ft``. Legacy aliases such as ``Z_kron`` and ``Z_sequence`` are also
accepted for compatibility.

Surge impedance and SIL
-----------------------

The scalar extraction uses the positive-sequence diagonal of the fully
transposed matrices. ``x1`` is in ohm/mile and ``b1`` is in microsiemens/mile;
the code divides ``b1`` by one million before taking the ratio. Nominal voltage
is in kV, so ``V_kV**2 / Z`` yields MW.

.. math::

   \begin{aligned}
   Z_{c} &= \sqrt{\frac{x_1}{b_1/10^6}}, \\
   \mathrm{SIL}_{MW} &= \frac{V_{LL,kV}^2}{Z_c}.
   \end{aligned}

The scalar equations and constants above describe the Python implementation
and parity fixture contract. Relevant implementation entry points are
``build_primitive_z``, ``build_primitive_p``, ``kron_reduce``,
``shunt_admittance``, ``fully_transpose``, ``sequence_matrix``, and
``calculate_electrical``. The nearest behavioral checks are in
``test/calculations/test_matrices.py`` and
``test/calculations/test_electrical_parity.py``.

Notation and units
------------------

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - Symbol
     - Meaning
     - Unit or convention
   * - ``R_ac``
     - Selected phase-conductor AC resistance
     - ohm/kilofoot input
   * - ``n_i``
     - Phase subconductor count
     - dimensionless
   * - ``GMR_i``, ``r_i``
     - Bundle GMR and equivalent radius
     - feet
   * - ``d_ij``, ``S_ij``
     - Direct and image distances
     - feet
   * - ``rho``
     - Earth resistivity
     - ohm-meter
   * - ``f``
     - Frequency
     - hertz
   * - ``R_C``, ``L_C``, ``L_F``
     - Julia-parity constants
     - 0.00158836, 0.00202237, 7.6786
   * - ``epsilon_air``
     - Potential-coefficient constant
     - 1.4240e-2 in the micro-unit contract
   * - ``Z``
     - Primitive/reduced series impedance
     - ohm/mile
   * - ``P``
     - Potential coefficient
     - 1/(microSiemens/mile) by implementation contract
   * - ``Y``
     - Reduced shunt admittance
     - microsiemens/mile
   * - ``a``
     - Positive-sequence operator ``exp(j 2 pi / 3)``
     - dimensionless
   * - ``V_LL,kV``
     - Nominal line-to-line voltage
     - kilovolt
   * - ``Z_c``, ``SIL``
     - Surge impedance and surge impedance loading
     - ohm, MW

The planning references describe the Julia computation flow and formulas; the
current Python functions and parity tests are authoritative where terminology
or unit interpretations differ. In particular, ``build_primitive_p`` retains
but discards its ``frequency`` argument, and the potential/admittance matrices
preserve the Julia micro-unit contract rather than normalizing all intermediate
values to SI units.