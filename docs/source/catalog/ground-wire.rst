Ground Wire
===========

The 27 ground-wire records consist of 26 Alumoweld sizes and one ACSR entry.
These rows have an ``awg_or_stranding`` field but **no codeword or AC
resistance**. Diameter is in inches; DC resistance is ohm/kft; breaking load
is pounds-force as recorded in the workbook; weight is lb/kft.

.. list-table:: Ground-wire inventory
   :header-rows: 1
   :widths: 13 9 18 17 17 18 16

   * - Family / stranding
     - Rows
     - Size (kcmil)
     - Diameter (in)
     - DC R (ohm/kft)
     - Breaking load (lb)
     - Weight (lb/kft)
   * - Alumoweld 37/5--37/10
     - 6
     - 384.2--1225
     - 0.713--1.270
     - 0.0425--0.1354
     - 52,950--142,800
     - 879--2802
   * - Alumoweld 19/5--19/10
     - 6
     - 197.3--628.9
     - 0.509--0.910
     - 0.0822--0.2622
     - 27,190--73,350
     - 448.7--1430
   * - Alumoweld 7/5--7/12
     - 8
     - 45.71--231.7
     - 0.242--0.546
     - 0.2264--1.127
     - 6301--27,030
     - 103.6--524.9
   * - Alumoweld 3/5--3/10
     - 6
     - 31.15--99.31
     - 0.220--0.392
     - 0.5177--1.651
     - 4532--12,230
     - 70.43--224.5
   * - ACSR 4/0 6/1
     - 1
     - 484.4
     - 0.251
     - 0.112121
     - 66,700
     - 1108

The ACSR ground-wire row is ``ACSR:4/0 6/1:484.4:27``. Its reported kcmil
size and weight appear inconsistent with its diameter; verify against the
source before using mechanical data. The runtime
:func:`transmissionlines.builders.line.ground_wire_from_record` only maps
diameter and DC resistance into ``GroundWireSpec``; breaking load and weight
remain catalog properties, not runtime equipment fields.