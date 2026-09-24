"""Public v3 API."""

from transmissionlines.builders.system import (
    BusDefinition,
    assemble_line_into_system,
    build_transmission_line,
)
from transmissionlines.catalog import CatalogRepository, generate_catalog
from transmissionlines.models import *
from transmissionlines.system import TransmissionLineSystem


def open_catalog(path: str, *, catalog_version: str | None = None) -> CatalogRepository:
    """Open a generated catalog repository."""
    return CatalogRepository(path, catalog_version=catalog_version)


__all__ = [
    "BusDefinition",
    "CatalogRepository",
    "TransmissionLineSystem",
    "assemble_line_into_system",
    "build_transmission_line",
    "generate_catalog",
    "open_catalog",
]
