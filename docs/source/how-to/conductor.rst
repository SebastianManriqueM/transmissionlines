Specify/Select a Conductor
==========================

See the :doc:`../catalog/phase-conductors` family table for sizes and units.
Codewords repeat across families and sometimes within one family. Use the
exact ``record_id`` or a combination that selects **one** row:

.. code-block:: python

   from transmissionlines.user_api import build

   catalog = build.open_catalog()
   choices = [choice for choice in catalog.conductors(family="ACCC")
              if choice["codeword"] == "IRVING"]
   print(catalog.format_choices(choices))
   conductor = build.conductor(catalog, record_id="ACCC:609.5:irving:uls")
   assert conductor.equipment.weight is not None
   assert conductor.equipment.rated_breaking_strength is not None
   assert conductor.equipment.total_material_area is not None

The IRVING choices include both ``standard`` and ``uls`` constructions. Select
one full ``record_id``; ``build.conductor`` never chooses a variant for you.
Catalog-backed components retain their versioned reference. Missing mechanical
measurements remain ``None``; sag reports missing required inputs instead of
inventing them.

For a diameter criterion, browse candidates and check family, codeword,
construction variant, published ampacity conditions, and resistance before
committing to one ``record_id``. Diameter is in inches. This is a **range search**,
not an automatic substitute for electrical or mechanical equivalence:

.. code-block:: python

   matches = catalog.conductors(family="ACSR", diameter_min_in=1.19,
                                diameter_max_in=1.20)
   print(catalog.format_choices(matches))
   conductor = build.conductor(catalog, record_id="ACSR:954:cardinal:standard:54/7")

Use manufacturer data and the lower-level :doc:`../reference/builders` for
components absent from the catalog. Electrical calculations need AC resistance
and enough geometry for bundle properties; St. Clair also needs ampacity.
For catalog records without a published GMR, the builder may estimate it from
outer radius and emit a warning. Verify that approximation for engineering
use. Assign the conductor to a circuit with ``build.tower``
(see :doc:`tower-configuration`).