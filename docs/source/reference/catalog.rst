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

The importer requires caller-supplied raw files and explicit header mappings.
It does not provide hidden workbook or manufacturer data.