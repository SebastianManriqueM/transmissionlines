How to
======

These recipes use the bundled ``data/catalog/v1`` snapshot from the repository
root. For other catalogs, pass their directory to ``open_catalog`` and check
its manifest and record IDs. Exact catalog selection raises
``NoCatalogMatch`` or ``AmbiguousCatalogMatch``; numerical filtering is an
explicit discovery step, not an implicit nearest-neighbor match.

.. toctree::
   :maxdepth: 2

   tower-geometry
   conductor
   ground-wire
   tower-configuration
   build-cross-section-line
   electrical-and-st-clair