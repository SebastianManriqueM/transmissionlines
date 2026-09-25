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
from transmissionlines.calculations.st_clair import calculate_st_clair, calculate_st_clair_curve_for_line
from transmissionlines.catalog import CatalogRepository, generate_catalog, generate_julia_workbook_catalog
from transmissionlines.models import *
from transmissionlines.system import TransmissionLineSystem
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.models.st_clair import StClairResult


def open_catalog(path: str, *, catalog_version: str | None = None) -> CatalogRepository:
    """Open a generated catalog repository."""
    return CatalogRepository(path, catalog_version=catalog_version)


def calculate_st_clair_curve(
    line_or_positive_sequence: object | None = None,
    *,
    positive_sequence: object | None = None,
    options: StClairOptions | None = None,
    sensitivities: dict[str, list[float]] | None = None,
) -> object:
    """Calculate a St. Clair result or return a copied line with it attached.

    A line input must already contain completed electrical parameters. Explicit
    mappings use natural units and return a standalone compact result.
    """
    from collections.abc import Mapping
    from transmissionlines.models.assets import TransmissionLine

    source = positive_sequence if positive_sequence is not None else line_or_positive_sequence
    if isinstance(source, TransmissionLine):
        return calculate_st_clair_curve_for_line(
            source, options=options, sensitivities=sensitivities
        )
    if not isinstance(source, Mapping):
        raise TypeError("provide a TransmissionLine or positive-sequence mapping")
    return calculate_st_clair(source, options=options, sensitivities=sensitivities)


def plot_st_clair_curve(
    result: StClairResult,
    *,
    curves: str = "base",
    x: str = "lengths_mi",
    y: str = "pr_mw",
    show_limits: bool = True,
    show_voltage_limit: bool = False,
    show: bool = False,
) -> object:
    """Plot a stored result, optionally showing voltage and its limit on a second axis."""
    from transmissionlines.plotting.st_clair import plot_st_clair_curve as plot_result

    return plot_result(
        result,
        curves=curves,
        x=x,
        y=y,
        show_limits=show_limits,
        show_voltage_limit=show_voltage_limit,
        show=show,
    )


__all__ = [
    "BusDefinition",
    "CatalogRepository",
    "TransmissionLineSystem",
    "assemble_line_into_system",
    "build_transmission_line",
    "calculate_electrical_parameters",
    "calculate_line_electrical_parameters",
    "calculate_st_clair_curve",
    "plot_st_clair_curve",
    "generate_catalog",
    "generate_julia_workbook_catalog",
    "open_catalog",
]
