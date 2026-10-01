Electrical models and equations
===============================

The electrical model and equations are based on Kersting's *Distribution
System Modeling and Analysis* [Kersting2012]_. The implementation orders phases
by circuit and A/B/C, then ground wires by wire ID. Geometry,
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

Cable GMR and series impedance
------------------------------

Phase-conductor cable GMR
~~~~~~~~~~~~~~~~~~~~~~~~~

The conductor builder resolves one phase-subconductor GMR in feet before the
electrical engine computes bundle GMR. It uses, in order, published catalog
``gmr_ft`` (when present), GMR derived from catalog internal reactance,
an optional independently sourced ``gmr_ft`` supplied by the caller, a verified
round ``6/1`` strand layout, and finally the overall-diameter approximation.
An external value is rejected when the catalog already provides published GMR
or internal reactance; it can replace either estimate. Without a diameter or
another source, the cable GMR remains unavailable. Catalog browsing reports
``published``, ``reactance-derived``, ``strand-estimated``,
``radius-estimated``, or ``missing`` without emitting construction warnings.

For a concentric round ``6/1`` ACSR, ACSR/AW, or ACSS row with source-backed
aluminum and core strand diameters, the builder checks that the core is one
strand, that the overall diameter fits one ring of six aluminum strands, and
that the aluminum and core strands have nearly equal diameters. In the absence
of measured strand current shares it **assumes equal current in all seven
strands, including steel**. With strand center distance :math:`d_{ij}`, strand
radius :math:`r_i`, and :math:`w_i=1/7`, its estimate is

.. math::

  \begin{aligned}
  d_{ii} &= r_i e^{-1/4}, \\
  \mathrm{GMR}_{6/1} &= \exp\left(\sum_{i=1}^{7}\sum_{j=1}^{7}
                 w_i w_j \ln d_{ij}\right).
  \end{aligned}

The core center is at the origin and the six aluminum centers are at 60-degree
intervals, each at the mean of the core and aluminum strand diameters from
the origin. Strand dimensions and :math:`d_{ij}` are in inches; divide the
result by 12 for feet. Equal steel and aluminum current is a simplifying
assumption, not a measured electrical property. If the geometry is absent or
inconsistent, including multilayer layouts such as ``54/7``, the builder
does not infer strand centers from counts. Instead it uses

.. math::

  \mathrm{GMR}_{\mathrm{radius}} = \frac{D_{\mathrm{outer}}}{24}e^{-1/4}
  \quad\text{feet, for }D_{\mathrm{outer}}\text{ in inches}.

This treats the entire cable as a solid round wire with its outside radius;
it is only a coarse proxy for stranded, composite, or shaped conductors.
Both estimated paths emit ``UserWarning`` at construction. Verify GMR against
engineering data before using either approximation for design or validation;
the warning is not emitted for published, reactance-derived, or independently
sourced GMR.

Primitive series impedance
~~~~~~~~~~~~~~~~~~~~~~~~~~

For conductor index :math:`i`, the diagonal uses bundle :math:`\mathrm{GMR}_i` and the
resistance of one subconductor divided by bundle count. For :math:`i \ne j`, the
mutual logarithm uses direct phase-to-phase distance :math:`d_{ij}`. The code uses
the same Carson earth-return correction for diagonal and mutual terms:

.. math::

   \begin{aligned}
   C_f &= L_F + \frac{1}{2}\ln\left(\frac{\rho}{f}\right), \\
   Z_{ii} &= 5.28\frac{R_{ac,i}}{n_i} + R_C f
            + j L_C f\left[\ln\left(\frac{1}{\mathrm{GMR}_i}\right)+C_f\right], \\
   Z_{ij} &= R_C f
            + j L_C f\left[\ln\left(\frac{1}{d_{ij}}\right)+C_f\right],\quad i\ne j.
   \end{aligned}

Here :math:`R_{ac,i}` is the selected phase AC resistance in ohm/kilofoot,
:math:`n_i` is the phase subconductor count, :math:`f` is frequency in hertz,
and :math:`\rho` is earth resistivity in ohm-meter. The Carson equation
coefficients used here are :math:`R_C = 0.00158836`,
:math:`L_C = 0.00202237`, and :math:`L_F = 7.6786`. Distances and GMR are in
feet; :math:`5.28` converts the selected ohm/kilofoot conductor resistance to the
implementation's ohm/mile scale. Ground-wire diagonal resistance uses its
DC resistance and its unbundled GMR. The off-diagonal resistance contribution
is :math:`R_C f` as implemented; it is not replaced with a more general earth-return
model.

Potential coefficients
----------------------

:math:`S_{ij}` is the distance to the image of conductor :math:`j` reflected below the
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

The potential-coefficient matrix :math:`P` uses the implementation's
:math:`1/(\mu\mathrm{S}/\mathrm{mile})` unit convention.
The Python ``build_primitive_p`` function retains a frequency argument for
interface compatibility but does not use it in this matrix.

Kron reduction and shunt admittance
-----------------------------------

Partition a primitive matrix into phase (:math:`p`) and ground-wire (:math:`g`) blocks.
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

For each three-phase circuit the implementation uses :math:`a = e^{j 2\pi/3}`
and the following phase-to-sequence transformation. Multi-circuit matrices use
one copy of :math:`T` per circuit on the block diagonal.

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
transposed matrices. :math:`x_1` is in ohm/mile and :math:`b_1` is in
microsiemens/mile; the code divides :math:`b_1` by one million before taking
the ratio. Nominal voltage is in kV, so :math:`V_{LL,\mathrm{kV}}^2/Z_c` yields MW.

.. math::

   \begin{aligned}
   Z_{c} &= \sqrt{\frac{x_1}{b_1/10^6}}, \\
   \mathrm{SIL}_{MW} &= \frac{V_{LL,kV}^2}{Z_c}.
   \end{aligned}

The scalar equations and coefficients above describe the Python implementation
and its validated unit conventions. Relevant implementation entry points are
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
   * - :math:`R_{ac,i}`
     - Selected phase-conductor AC resistance
     - ohm/kilofoot input
   * - :math:`n_i`
     - Phase subconductor count
     - dimensionless
   * - :math:`\mathrm{GMR}_i`, :math:`r_i`
     - Bundle GMR and equivalent radius
     - feet
   * - :math:`d_{ij}`, :math:`S_{ij}`
     - Direct and image distances
     - feet
   * - :math:`\rho`
     - Earth resistivity
     - ohm-meter
   * - :math:`f`
     - Frequency
     - hertz
   * - :math:`R_C`, :math:`L_C`, :math:`L_F`
     - Carson equation coefficients used by this implementation
     - 0.00158836, 0.00202237, 7.6786
   * - :math:`\epsilon_{air}`
     - Potential-coefficient constant
     - 1.4240e-2 in the micro-unit contract
   * - :math:`Z`
     - Primitive/reduced series impedance
     - ohm/mile
   * - :math:`P`
     - Potential coefficient
     - 1/(microSiemens/mile) by implementation contract
   * - :math:`Y`
     - Reduced shunt admittance
     - microsiemens/mile
   * - :math:`a`
     - Positive-sequence operator :math:`e^{j 2\pi/3}`
     - dimensionless
   * - :math:`V_{LL,\mathrm{kV}}`
     - Nominal line-to-line voltage
     - kilovolt
   * - :math:`Z_c`, :math:`\mathrm{SIL}`
     - Surge impedance and surge impedance loading
     - ohm, MW

The current Python functions and tests determine the exact numerical and unit
conventions used here. In particular, ``build_primitive_p`` retains but
discards its ``frequency`` argument, and the potential/admittance matrices use
the documented micro-unit convention rather than normalizing all intermediate
values to SI units.

Reference
---------

.. [Kersting2012] Kersting, W. H. (2012). *Distribution System Modeling and
  Analysis* (3rd ed.). CRC Press. `https://doi.org/10.1201/b11697
  <https://www.taylorfrancis.com/books/mono/10.1201/b11697/distribution-system-modeling-analysis-william-kersting>`_.