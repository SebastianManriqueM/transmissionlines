Phase Conductors
================

The default v2 catalog contains 641 PDF-backed conductors. Select a specific
``record_id`` or an exact combination of family, codeword, size, and variant;
see :doc:`../how-to/conductor`. The ``ACCC`` family has standard and ULS
variants, ACSS has strength variants, and ACSS/TW contains shaped-wire rows. A codeword
alone is not a unique selector. The PDF-backed fields include weight (lb/kft),
rated breaking strength (lb), total material area (in2), and temperature-specific
resistance and ampacity. Missing measurements remain null. ``ConductorV2Record``
retains the original conditions; the runtime equipment maps weight and strength
to force units (lbf/kft and lbf) and only a published 75 C ampacity to the
unqualified ``ampacity`` field.

.. list-table:: Default v2 phase-conductor inventory
   :header-rows: 1
   :widths: 22 12 66

   * - Family
     - Rows
     - Variants and published electrical conditions
   * - AAC
     - 56
     - 75 C AC resistance and ampacity; 20 C DC resistance
   * - ACCC
     - 48
     - Standard and ULS; 25/200 C AC resistance, 75/180/200 C ampacity
   * - ACSR
     - 68
     - 75 C AC resistance and ampacity; 20 C DC resistance
   * - ACSR/AW
     - 61
     - 75 C AC resistance and ampacity; 20 C DC resistance
   * - ACSS
     - 192
     - Standard, high, and HS285; 75 C AC resistance, 200 C ampacity
   * - ACSS/TW
     - 216
     - Shaped-wire variants; 25/50/75 C AC resistance, 75/200 C ampacity

Selecting a v2 record
---------------------

Use the full ``record_id`` or include ``variant`` when a family and codeword
identify multiple constructions. For example:

.. code-block:: python

   from transmissionlines.api import open_catalog
   from transmissionlines.catalog.schemas import ConductorV2Record

   catalog = open_catalog()
   row = catalog.select_exact(
       "conductors", record_id="ACSR:954:cardinal:standard:54/7"
   )
   record = ConductorV2Record.model_validate(row)

``select_exact`` raises ``AmbiguousCatalogMatch`` rather than selecting a
variant implicitly. The builder prefers published AC resistance at 75 C,
then 50 C, then 25 C; it does not substitute a 200 C or generic value when
these are absent. Missing measurements remain ``None``. Consult the record's
temperature-specific columns and provenance before using ratings in a
calculation.