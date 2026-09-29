Build a ``CrossSectionTransmissionLine``
========================================

This complete script runs from the repository root using the bundled catalog.
It selects structure ``3L11`` (two circuits), validates all selected Parquet
rows as catalog records, builds positions, two circuits and one shared ground
wire spec, and creates a representative 345 kV line. No geographic supports
or span lengths are required for a cross-section. The final lines also run a
short calculation; see :doc:`electrical-and-st-clair` for interpreting it.

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
recipes and the independent in-memory example in :doc:`../quickstart`.