Catalog
========

The default ``data/catalog/v2`` contains 641 PDF-backed conductor records and
retains the tower workbook's 70 geometries, 27 ground wires, and other
non-conductor tables. ``data/catalog/v1`` preserves the historical workbook
snapshot with 161 phase conductors. The phase-conductor page leads with v2 and
documents only its PDF-backed records. Inventory counts describe shipped
records, not engineering limits or interchangeability guarantees. Inspect and
select an individual record before building a line.

.. toctree::
   :maxdepth: 2

   tower-geometry
   phase-conductors
   ground-wire

Source files are not needed to *read* either snapshot; they are needed to
regenerate it. See :doc:`../concepts/catalog` for provenance.