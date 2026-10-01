Build a ``CrossSectionTransmissionLine``
========================================

This complete script runs from the repository root using the bundled catalog.
It selects structure ``3L11`` (two circuits) and exact conductor and ground-wire
IDs, then uses ``build.tower`` and ``build.cross_section_line`` to create a
representative 345 kV line. No geographic supports or span lengths are needed
for a cross-section. The final lines run a short calculation; see
:doc:`electrical-and-st-clair` for interpreting it. Cardinal's v2 row has no
published GMR: the conductor builder warns when it estimates GMR from outer
radius. Verify that approximation for engineering use.

.. literalinclude:: examples/catalog_line.py
   :language: python
   :linenos:

Run it from a checkout after ``uv sync --locked``:

.. code-block:: console

   uv run python docs/source/how-to/examples/catalog_line.py

Expected output is ``complete`` followed by ``2`` St. Clair curves, one per
circuit. The insulator, 60 Hz frequency, 100 ohm-meter earth resistivity, and
20-mile St. Clair range are illustrative choices, not properties selected
from the catalog. To use custom components instead, follow the four preceding
recipes and the lower-level :doc:`../reference/builders`.