How to
======

All catalog-backed recipes use the bundled ``data/catalog/v2`` snapshot by
default through ``open_catalog()``. Pass an explicit directory only when
opening another version, and check its manifest and record IDs. Exact selection
raises ``NoCatalogMatch`` or ``AmbiguousCatalogMatch``; numerical filtering is an
explicit discovery step, not an implicit nearest-neighbor match.

.. toctree::
   :maxdepth: 2

   tower-geometry
   conductor
   ground-wire
   tower-configuration
   build-cross-section-line
   electrical-and-st-clair