"""Construct catalog-backed cross sections and calculate their results."""

from pathlib import Path

from transmissionlines.models.cables import BundleSpec
from transmissionlines.user_api.analysis import calculations
from transmissionlines.user_api.catalog import BrowsingCatalog
from transmissionlines.user_api.components import (
    configure_tower as tower,
    select_conductor as conductor,
    select_ground_wire as ground_wire,
)
from transmissionlines.user_api.lines import add_line, cross_section_line, system


def open_catalog(
    path: str | Path = "data/catalog/v2", *, catalog_version: str | None = None
) -> BrowsingCatalog:
    """Open a versioned catalog for explicit discovery and selection.

    Parameters
    ----------
    path : str or Path, optional
        Directory containing the normalized catalog snapshot.
    catalog_version : str, optional
        Override the version in the catalog manifest.

    Returns
    -------
    BrowsingCatalog
        Read-only browsing handle.
    """
    return BrowsingCatalog(path, catalog_version=catalog_version)


def bundle(*, subconductor_count: int, subconductor_spacing_in: float | None = None) -> BundleSpec:
    """Select a bundle with adjacent center-to-center spacing in inches."""
    return BundleSpec(subconductor_count=subconductor_count, subconductor_spacing_in=subconductor_spacing_in)

__all__ = [
    "add_line",
    "bundle",
    "calculations",
    "conductor",
    "cross_section_line",
    "ground_wire",
    "open_catalog",
    "system",
    "tower",
]
