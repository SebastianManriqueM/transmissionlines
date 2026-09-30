"""Check that unqualified catalog access uses the published v2 snapshot."""

from transmissionlines.api import open_catalog


def test_open_catalog_defaults_to_v2() -> None:
    catalog = open_catalog()

    assert catalog.catalog_version == "v2"
    assert len(catalog.table("conductors")) == 641


def test_open_catalog_can_explicitly_select_v1() -> None:
    catalog = open_catalog("data/catalog/v1")

    assert catalog.catalog_version == "v1"