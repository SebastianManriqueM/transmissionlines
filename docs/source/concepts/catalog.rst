Reference catalog
=================

The catalog is a versioned reference-data layer, separate from runtime line
components. A catalog build consumes caller-provided source artifacts and
explicit source-header mappings, normalizes the records into tables, validates
the schema, and writes a manifest containing source SHA-256 checksums, row
counts, versions, and declared units. Missing mapped headers are errors; the
importer does not guess columns by position.

The normalized catalog contains geometry, phase and ground-wire locations,
conductor and ground-wire records, state identity and borders, and preserved
actual-line records. The runtime repository reads Parquet tables. Selection is
exact and deterministic: state matching uses FIPS code, USPS code, or canonical
name; exact record selection raises on no match or ambiguous matches.

Runtime builders may attach a ``CatalogReference`` containing catalog version,
table name, record ID, and optional source ID. They do not embed the selected
raw row. This keeps calculated line models compact and independent of source
workbooks. This checkout includes ``data/catalog/v1`` from the tower workbook
and ``data/catalog/v2`` with PDF-backed conductors. V2 copies all non-conductor
tables from v1; its manifest pins source checksums and its provenance, issue,
source, and crosswalk tables support auditing. Regeneration uses
``python scripts/build_conductor_catalog_v2.py`` and refuses to overwrite an
existing destination. The v1 importer remains a separate workbook pipeline.

V2 conductor rows distinguish ``family``, ``codeword``, ``size``, and
``variant``. They expose weight in lb/kft, rated strength in lb, and total
material area in in2, with nullable values and per-field provenance.
``BareConductorEquipment`` converts these to lbf/kft, lbf, and in2 quantity
types. No modulus or thermal expansion is inferred from the PDFs; provide
those independently for sag. Runtime AC resistance uses published 75 C, then
50 C, then 25 C values; only published 75 C ampacity maps to the unqualified
equipment field. Higher-temperature ratings stay in the catalog.

The data path separates one-time catalog generation from runtime reads:

.. mermaid::
   :name: catalog-generation-and-use
   :alt: Source workbook normalization, catalog validation, exact runtime selection, and model construction
   :caption: Catalog generation and runtime use

   flowchart TD
	   Source[Workbook and pinned PDFs] --> Normalize[Normalize mapped records]
	   Mapping[Explicit source adapters] --> Normalize
	   Normalize --> Validate{Catalog valid}
	   Validate -->|no| Reject[Reject catalog build]
	   Validate -->|yes| Tables[Write versioned Parquet tables]
	   Tables --> Manifest[Write checksum and schema manifest]
	   Tables --> Repository[Open read-only catalog repository]
	   Manifest --> Repository
	   Repository --> Select[Select exact state and records]
	   Select --> Build[Build typed runtime models]
	   Build --> Provenance[Attach compact catalog references]

The existing repository notes remain in ``docs/catalog_v3.md`` and
``docs/electrical_parity_and_catalog.md``. Their catalog schema, provenance,
and selection behavior is reflected here and in the electrical user guide.
See :doc:`../catalog/index` for the bundled inventory,
:doc:`../how-to/index` for practical selection, and
:doc:`../reference/catalog` for import, validation, and repository APIs.