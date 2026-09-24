# Versioned catalogs

`v1` is generated from `data/raw/Tower_geometries_DB.xlsx` using the catalog
adapter in `transmissionlines.catalog.importer`. It contains normalized
Parquet tables for the geometry, phase positions, ground-wire positions,
conductors, ground wires, states, state borders, and original line dataset.

The manifest records the source checksum and table schemas. Validate it with:

```powershell
python -c "from transmissionlines.catalog import validate_catalog; assert not validate_catalog('data/catalog/v1')"
```
