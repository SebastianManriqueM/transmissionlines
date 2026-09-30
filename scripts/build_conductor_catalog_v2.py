"""Generate the v2 PDF-backed conductor catalog without changing v1."""

from pathlib import Path

from transmissionlines.catalog.conductor_v2_build import build_conductor_catalog
from transmissionlines.catalog.validation import require_valid_catalog


def main() -> None:
    """Build and validate the checked PDF-backed v2 catalog."""
    root = Path(__file__).resolve().parents[1]
    output = root / "data/catalog/v2"
    build_conductor_catalog(root, output)
    require_valid_catalog(output, source_root=root)
    print(f"Validated v2 catalog: {output}")


if __name__ == "__main__":
    main()