Catalog
========

The bundled ``data/catalog/v1`` directory contains a normalized, versioned
snapshot of the tower workbook: 70 geometries, 161 phase conductors, and 27
ground wires. The tables below classify **all** records by tower voltage and
structure or cable family. Ranges describe the rows in the shipped Parquet
files, not engineering limits or interchangeability guarantees. Use the
repository to inspect and select an individual record before building a line.

.. toctree::
   :maxdepth: 2

   tower-geometry
   phase-conductors
   ground-wire

The workbook's original source files are not needed to *read* this snapshot;
they are needed only to regenerate it. See :doc:`../concepts/catalog` for
provenance.