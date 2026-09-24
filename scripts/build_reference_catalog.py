"""Build the checked-in v1 catalog from the preserved Julia workbook."""

from pathlib import Path

from transmissionlines.catalog import generate_julia_workbook_catalog


ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    generate_julia_workbook_catalog(
        ROOT / "data/raw/Tower_geometries_DB.xlsx",
        ROOT / "data/catalog/v1",
        catalog_version="v1",
    )
