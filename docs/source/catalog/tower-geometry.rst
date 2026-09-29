Tower Geometry
==============

Each tower row identifies a structure code and (where recorded) a nominal
voltage, circuit count, ground-wire count, and free-text state description.
The following groups account for all 70 geometry rows in ``v1``. Codes in a
range are inclusive; ``EX_*`` rows are workbook examples, and ``DC1``/``DC2``
have no structure type or conductor positions needed to form a cross-section.

.. list-table:: Tower inventory
   :header-rows: 1
   :widths: 12 15 23 9 11 12 18

   * - kV
     - Structure
     - Codes
     - Rows
     - Circuits
     - Ground wires
     - Known locations (examples)
   * - 33
     - Pole
     - EX_K4_1
     - 1
     - 1
     - 1
     - Example (not a state)
   * - 230
     - H frame / lattice / pole
     - 2H1_PVOGTLE, 2L1_ASEC, 2P1_ASEC
     - 3
     - 1--2
     - 2
     - Georgia (2H1); others unknown
   * - 255
     - Lattice
     - EX_ST4_14
     - 1
     - 1
     - 1
     - Example (not a state)
   * - 345
     - H frame
     - 3H1--3H10
     - 10
     - 1--2
     - 2
     - NH, UT, ME, IL, NY, CT, VT, WI, NM, KS, MN, MO, MA
   * - 345
     - Lattice
     - 3L1--3L15
     - 15
     - 1--2
     - 2
     - IA, IN, CO, MI, PA, OH, NY, OK, MA, TX, UT, MO, IL
   * - 345
     - Pole
     - 3P1--3P8
     - 8
     - 1--2
     - 1--2
     - OH, IN, CT, MN, WI, NY, TX, LA, UT, IL
   * - 345
     - Y
     - 3Y1--3Y3
     - 3
     - 1
     - 2
     - AZ, WY, LA
   * - 500
     - H frame
     - 5H1--5H2
     - 2
     - 1--2
     - 2
     - MD (5H1); 5H2 unknown
   * - 500
     - Lattice
     - 5L1--5L14
     - 14
     - 1--2
     - 1--2
     - WA, OR, ID, MT, WY, UT, NV, CA, ND, SD, CO, NM, MN, IA, NC, AL, MD, VA, AZ, SC; some unknown
   * - 500
     - Pole
     - 5P1--5P2
     - 2
     - 1
     - 1--2
     - Unknown
   * - 500
     - Y
     - 5Y1--5Y3
     - 3
     - 1
     - 2
     - AR, AL; 5Y1 unknown
   * - 735
     - Unspecified
     - DC1, DC2
     - 2
     - Unspecified
     - Unspecified
     - Unknown
   * - 765
     - H frame / lattice / pole / V frame
     - 7H1, 7L1--7L3, 7P1, 7V1
     - 6
     - 1
     - 2
     - Unknown (7L1 is marked ``xxxx``)

State labels above are **source descriptions**, not validated state membership;
some contain duplicates, a placeholder, or a multi-state service area. For
exact code-to-state mapping, inspect ``state`` on each geometry row. The
``phase_positions`` and ``ground_wire_positions`` tables supply coordinates
in feet; those positions, rather than the counts alone, determine whether a
geometry can be used.