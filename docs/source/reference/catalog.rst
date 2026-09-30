Catalog APIs
============

Catalog-generation and validation operations are exported from
``transmissionlines.api``. ``CatalogRepository`` provides read-only exact
selection from normalized Parquet tables. See :doc:`../concepts/catalog` for
the storage boundary and provenance model.

Repository and selection errors
--------------------------------

.. automodule:: transmissionlines.catalog.repository
   :members: CatalogSelectionError, NoCatalogMatch, AmbiguousCatalogMatch, CatalogRepository

Catalog import and validation functions
----------------------------------------

.. automodule:: transmissionlines.catalog.importer
   :members: generate_catalog, generate_julia_workbook_catalog, sha256_file

.. automodule:: transmissionlines.catalog.validation
   :members:

Exact selection helpers
-----------------------

.. automodule:: transmissionlines.catalog.selection
   :members:

The workbook importer requires caller-supplied raw files and explicit header
mappings. The separate v2 builder reads pinned local PDF sources; it does not
use the workbook conductor table. Select v2 rows with ``CatalogRepository``
and validate them with ``ConductorV2Record``. The v1-to-v2 crosswalk is an
audit table, not an automatic reference redirect. ``open_catalog()`` defaults
to v2 for new selections; open ``data/catalog/v1`` explicitly for existing
v1 references. Unresolved crosswalk entries need no adjudication for new
v2 selections.

V2 PDF build
------------

.. automodule:: transmissionlines.catalog.conductor_v2_build
   :members: build_conductor_catalog