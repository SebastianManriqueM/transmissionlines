# v3 reference catalog

The repository includes the v1 source workbook and the pinned manufacturer PDFs used for the v2 conductor catalog. The generic `generate_catalog` API still requires caller-provided raw artifacts and explicit source-header mappings; it rejects missing headers rather than using positional columns. The separate v2 build uses checked local PDFs and publishes source-derived conductors with field provenance. Sources are hashed with SHA-256 and the generated manifest records checksums, row counts, and schema/catalog versions.

Generated catalogs live in `data/catalog/<version>/` and are queried with `CatalogRepository`. `open_catalog()` defaults to v2 for new selections; open `data/catalog/v1` explicitly for saved v1 references. State selection accepts one exact FIPS code, USPS code, or canonical name. Border expansion uses exact normalized keys only; it never performs substring matching or fallback broadening.

The static catalog models keep records separate from runtime components. Runtime builders should attach version-qualified `CatalogReference` values and must not embed source rows. The v1-to-v2 conductor crosswalk is for audit, not automatic remapping; unresolved entries do not block new v2 selections. For the published inventory and build instructions, see `../data/catalog/README.md`.
