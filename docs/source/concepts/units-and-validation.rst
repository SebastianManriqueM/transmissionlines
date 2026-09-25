Units and validation
====================

Unit boundary
-------------

The public data models use typed quantities backed by the Infrasys quantity
system. Construct quantities with an explicit magnitude and unit, as in
``VoltageKV(230, "kilovolt")``. Calculation orchestration converts compatible
inputs to the unit required by each calculation; for example, voltage to kV,
frequency to Hz, earth resistivity to ohm-meter, and conductor resistance to
ohm/kilofoot.

.. list-table::
   :header-rows: 1

   * - Quantity
     - Model/input convention
     - Calculation/result convention
   * - Tower coordinates and cable distances
     - feet
     - feet in geometry and logarithmic terms
   * - Conductor diameter and bundle spacing
     - inches
     - converted to feet where needed
   * - Phase AC and ground-wire DC resistance
     - ohm/kilofoot
     - ohm/mile in series matrices
   * - Nominal line voltage
     - kV
     - kV for SIL; V line-to-line at the St. Clair boundary
   * - Frequency
     - Hz
     - Hz
   * - Earth resistivity
     - ohm-meter
     - ohm-meter in the Julia-parity correction
   * - Sequence resistance/reactance
     - ohm/mile
     - ohm/mile
   * - Sequence susceptance
     - microsiemens/mile
     - microsiemens/mile; converted to S/mile for St. Clair
   * - Surge impedance and SIL
     - ohm and MW
     - ohm and MW
   * - St. Clair curve powers
     - W and MW
     - W and MW
   * - Route distances
     - miles
     - miles

Validation boundaries
---------------------

Model validation ensures:

* nominal voltage, frequency, and earth resistivity are positive;
* terminal bus names are distinct and line/component names are consistent;
* each circuit has one A, B, and C phase, with no duplicate positions;
* at least one ground-wire location exists;
* there is one phase specification per circuit;
* bundle counts are positive, bundle spacing is present and positive for
  multi-subconductor bundles, and absent for a single conductor;
* electrical matrix dimensions, labels, units, and required result scalars are
  consistent with one- or two-circuit topology; and
* a completed St. Clair curve has parallel arrays of equal length.

The electrical calculation reports missing conductor fields and invalid
circuit-to-specification mappings as actionable ``ValueError`` subclasses.
Direct St. Clair mappings require nominal voltage, positive-sequence
``r_ohm_per_mile``, ``x_ohm_per_mile``, susceptance, and conductor ampacity.
For a bundle, the thermal current limit uses the per-subconductor ampacity
multiplied by the subconductor count.

Canonical result labels
-----------------------

Matrices carry explicit units and deterministic labels. Phase rows follow
circuit order and A/B/C order; ground-wire rows follow wire ID. Sequence rows
are labelled ``<circuit-number>:zero``, ``:positive``, and ``:negative``.
Canonical scalar names include ``r1``, ``x1``, ``b1``, ``surge_impedance_ohm``,
and ``sil_mw``. Two-circuit results also include zero-sequence mutual scalars,
while each circuit's diagonal positive-sequence values are stored under
``circuit_scalars``.