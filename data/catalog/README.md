# Versioned catalogs

`v1` is generated from `data/raw/Tower_geometries_DB.xlsx` using the catalog
adapter in `transmissionlines.catalog.importer`. It contains normalized
Parquet tables for the geometry, phase positions, ground-wire positions,
conductors, ground wires, states, state borders, and original line dataset.

The manifest records the source checksum and table schemas. Validate it with:

```powershell
python -c "from transmissionlines.catalog import validate_catalog; assert not validate_catalog('data/catalog/v1')"
```

`v2` replaces only the conductor table with checked PDF-backed candidates. All
other v1 Parquet tables are copied unchanged. Generate it once with:

```powershell
python scripts/build_conductor_catalog_v2.py
```

The build refuses to overwrite an existing v2 directory and checks the pinned
workbook and eight PDF checksums. Its manifest contains source and table hashes,
schema and parser versions, and row counts. `conductor_provenance.parquet` retains
field-level source cells and derivation notes; `conductor_issues.parquet` retains
the printed TW differences, absent ULS strengths, and rejected Bluebird transfer.
`conductor_crosswalk.parquet` maps only unique exact legacy identities and records
unmapped, ambiguous, and excluded cases without redirecting v1 references.
Temperature-specific electrical fields are explicit; ACCC resistance values are
converted from ohm/mile to ohm/kft, with original values in provenance. The
HS285 TW electrical pages are joined to geometry pages by section, codeword,
size, and type; their source pages remain distinct in the provenance sidecar.
Missing measurements remain null rather than inferred.

Validate the built catalog and original source artifacts with:

```powershell
python -c "from transmissionlines.catalog.validation import require_valid_catalog; require_valid_catalog('data/catalog/v2', source_root='.')"
```
