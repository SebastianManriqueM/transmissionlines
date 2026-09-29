Phase Conductors
================

The 161 conductor rows cover the following families. Sizes are kcmil;
diameters are inches; AC and DC resistances are ohm/kft. Values in each range
are minima and maxima across records, **not** paired properties of one cable.
Select a specific ``record_id`` for its codeword, stranding and measured
properties. The catalog has no conductor breaking-load or weight columns.

.. list-table:: Phase-conductor inventory
   :header-rows: 1
   :widths: 10 9 18 17 18 18 15

   * - Family
     - Rows
     - Size (kcmil)
     - Diameter (in)
     - AC R (ohm/kft)
     - DC R (ohm/kft)
     - Ampacity (A)
   * - AAAC
     - 12
     - 312.8--1439.2
     - 0.642--1.382
     - 0.017167--0.37877
     - 0.014--0.3089
     - 362--897
   * - AAC
     - 16
     - 266.8--2500
     - 0.593--1.823
     - 0.0097--0.0794
     - 0.00699--0.0648
     - 445--1700
   * - ACAR
     - 28
     - 503.6--2493
     - 0.814--1.821
     - 0.01--0.0433
     - 0.0074--0.0354
     - 760--1670 (some missing)
   * - ACCC
     - 28
     - 383.2--2740.6
     - 0.68--1.762
     - 0 (source placeholder)
     - 0.006174--0.04392
     - 558--1808 (some missing)
   * - ACSR
     - 32
     - 266.8--2156
     - 0.609--1.762
     - 0.0105--0.0788
     - 0.00801--0.0644
     - 445--1610
   * - ACSS
     - 45
     - 266.8--2312
     - 0.642--1.802
     - 0.01--0.0762
     - 0.007--0.0619
     - Not recorded

.. list-table:: Representative codewords and stranding by family
   :header-rows: 1
   :widths: 12 44 44

   * - Family
     - Codewords (examples)
     - Stranding (examples)
   * - AAAC
     - 1439_2, 1348_8, 1259_6
     - 61/0, 37/0, 19/0
   * - AAC
     - Laurel, Tulip, Cosmos
     - 19/0, 37/0, 61/0, 91/0
   * - ACAR
     - Pelican, Osprey, Dove
     - 15/4, 18/19, 12/7, 30/7
   * - ACCC
     - OCEANSIDE, LINNET, ORIOLE
     - 26/0, 26/1, 26/2, 26/3
   * - ACSR
     - Waxwing, Partridge, Merlin, Cardinal
     - 18/1, 26/7, 30/7, 54/7
   * - ACSS
     - Partridge, Oriole, Linnet
     - 26/7, 30/7, 24/7, 30/19

``codeword`` and ``stranding`` are per-record fields. For example, the
``ACSR:Cardinal:954.0:21`` row is Cardinal ACSR, 54/7 stranding, 954 kcmil,
1.196 in diameter, 0.0179 ohm/kft DC resistance, and 0.0222 ohm/kft AC
resistance at 75 C; its recorded ampacity is 990 A. The same codeword occurs
in **other families and stranding variants**, so codeword alone is not a
unique selector. Temperature-specific AC columns (25, 50, 75 C) are available
on some rows; :func:`transmissionlines.builders.line.conductor_from_record`
prefers the 75 C value, then 50 C, then 25 C, then the generic AC field.
Missing or zero source values are not inferred from the family or diameter.