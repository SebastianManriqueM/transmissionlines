"""Public v3 API."""

from transmissionlines.builders.system import (
    BusDefinition,
    assemble_line_into_system,
    build_transmission_line,
)
from transmissionlines.calculations.electrical import (
    calculate_electrical_parameters,
    calculate_line_electrical_parameters,
)
from transmissionlines.catalog import CatalogRepository, generate_catalog, generate_julia_workbook_catalog
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
    "calculate_electrical_parameters",
    "calculate_line_electrical_parameters",
    "generate_catalog",
    "generate_julia_workbook_catalog",
    "open_catalog",
]
