"""Public API for input-graph calculations and catalog access."""

from collections.abc import Mapping

from transmissionlines.builders.system import (
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
from transmissionlines.models.assets import CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.calculation_result import LineCalculationResult
from transmissionlines.models.routing import ElectricalTower
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.models.st_clair import StClairResult
from transmissionlines.plotting.st_clair import plot_st_clair_curve as plot_result


def open_catalog(path: str = "data/catalog/v2", *, catalog_version: str | None = None) -> CatalogRepository:
    """Open a generated, normalized catalog repository.

    Parameters
    ----------
    path : str, optional
        Path to a catalog directory containing normalized Parquet tables.
        Defaults to the bundled v2 catalog relative to the working directory.
    catalog_version : str, optional
        Explicit catalog version. If omitted, use the version in the manifest
        when available.

    Returns
    -------
    CatalogRepository
        Read-only exact-selection interface for the catalog.
    """
    return CatalogRepository(path, catalog_version=catalog_version)


def calculate_st_clair_curve(
    line_or_positive_sequence: object | None = None,
    *,
    previous: LineCalculationResult | None = None,
    tower: ElectricalTower | None = None,
    positive_sequence: object | None = None,
    options: StClairOptions | None = None,
    sensitivities: dict[str, list[float]] | None = None,
) -> StClairResult:
    """Calculate a standalone St. Clair result from a line or explicit constants.

    A line input requires a matching external electrical result. Explicit
    mappings use natural units; neither path mutates a registered component.

    Parameters
    ----------
    line_or_positive_sequence : concrete transmission line or mapping, optional
        Input line or mapping with nominal voltage, positive-sequence
        resistance/reactance, shunt susceptance, and conductor ampacity.
    previous : LineCalculationResult, optional
        Required prior electrical result when the input is a line.
    tower : ElectricalTower, optional
        Explicit selected support for a heterogeneous routed line.
    positive_sequence : mapping, optional
        Explicit mapping input. When provided, it takes precedence over
        ``line_or_positive_sequence``.
    options : StClairOptions, optional
        Voltage, compensation, angle, and line-length settings.
    sensitivities : mapping, optional
        St. Clair option names mapped to sampled values for sensitivity curves.

    Returns
    -------
    StClairResult
        Standalone curve result for the selected cross-section or mapping.

    Raises
    ------
    TypeError
        If the input is neither a concrete line nor a positive-sequence mapping.
    ValueError
        If a line lacks complete electrical parameters or required inputs.
    """
    source = positive_sequence if positive_sequence is not None else line_or_positive_sequence
    if isinstance(source, (CrossSectionTransmissionLine, RoutedTransmissionLine)):
        if previous is None:
            raise ValueError("line calculation requires a previous electrical result")
        return calculate_st_clair_curve_for_line(
            source, previous, tower=tower, options=options, sensitivities=sensitivities
        )
    if not isinstance(source, Mapping):
        raise TypeError("provide a concrete line or positive-sequence mapping")
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
    """Plot stored St. Clair arrays without recalculating the curve.

    Parameters
    ----------
    result : StClairResult
        Previously calculated curve result.
    curves : {'base', 'all'}, optional
        Plot base curves only, or include sensitivity curves.
    x : {'lengths_mi'}, optional
        Stored length array used on the horizontal axis.
    y : {'pr_mw', 'pr_w', 'ps_mw', 'ps_w'}, optional
        Stored power array used on the vertical axis.
    show_limits : bool, optional
        Mark points by their active limiting criterion.
    show_voltage_limit : bool, optional
        Add receiving-end voltage and the configured threshold on a second
        axis.
    show : bool, optional
        Call ``matplotlib.pyplot.show`` after creating the plot.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the selected stored curves.

    Raises
    ------
    ImportError
        If Matplotlib is unavailable in the current environment.
    ValueError
        If the selected curve or axis name is unsupported.
    """
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
