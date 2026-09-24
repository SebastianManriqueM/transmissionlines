# v3 reference catalog

The repository currently contains no workbook or manufacturer source artifacts. No source-derived values or invented mappings are checked in. `generate_catalog` therefore requires caller-provided raw artifacts and explicit source-header mappings; it rejects missing headers rather than using positional columns. Sources are hashed with SHA-256 and the generated manifest records checksums, row counts, schema/catalog versions, and units supplied by the normalized source.

Generated catalogs live in `data/catalog/<version>/` and are queried with `CatalogRepository`. State selection accepts one exact FIPS code, USPS code, or canonical name. Border expansion uses exact normalized keys only; it never performs substring matching or fallback broadening.

The static v3 models keep catalog records separate from runtime components. Runtime builders should attach `CatalogReference` and must not embed source rows.
