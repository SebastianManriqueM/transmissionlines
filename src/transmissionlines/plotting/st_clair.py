"""Optional Matplotlib adapter for stored St. Clair curve results."""

import importlib
from typing import Any

from transmissionlines.models.st_clair import StClairResult

TICK_LABEL_SIZE_PT = 14
AXIS_LABEL_SIZE_PT = 14
AXIS_TITLE_SIZE_PT = 16
LEGEND_SIZE_PT = 14
LINE_WIDTH_PT = 2.5


def plot_st_clair_curve(
    result: StClairResult,
    *,
    curves: str = "base",
    x: str = "lengths_mi",
    y: str = "pr_mw",
    show_limits: bool = True,
    show_voltage_limit: bool = False,
    show: bool = False,
) -> Any:
    """Plot stored loadability arrays without recalculating them.

    Parameters
    ----------
    result : StClairResult
        Previously calculated St. Clair result.
    curves : {'base', 'all'}, optional
        Select base curves or base plus sensitivities.
    x : {'lengths_mi'}, optional
        Curve length array used for the horizontal axis.
    y : {'pr_mw', 'pr_w', 'ps_mw', 'ps_w'}, optional
        Stored power array used for the vertical axis.
    show_limits : bool, optional
        Mark samples by their active limiting criterion.
    show_voltage_limit : bool, optional
        Plot receiving-end voltage on a secondary axis with the configured
        voltage-drop threshold.
    show : bool, optional
        Call pyplot.show after constructing the axes.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the selected stored curve arrays.

    Raises
    ------
    ImportError
        If the optional ``plot`` dependency is not installed.
    ValueError
        If a requested field or curve selection is unsupported.
    """
    try:
        plt = importlib.import_module("matplotlib.pyplot")
    except ImportError as error:
        raise ImportError("plotting requires the optional 'plot' dependency") from error

    if x != "lengths_mi" or y not in {"pr_mw", "pr_w", "ps_mw", "ps_w"}:
        raise ValueError("unsupported St. Clair plot axis")
    if curves not in {"base", "all"}:
        raise ValueError("curves must be 'base' or 'all'")
    axes = plt.gca()
    selected = list(result.curves)
    if curves == "all":
        selected.extend(result.sensitivity_curves)
    colors = {"voltage_drop": "#d34b3f", "steady_state_stability": "#267d68", "thermal_ampacity": "#d39b28"}
    for curve in selected:
        axes.plot(
            curve.lengths_mi,
            getattr(curve, y),
            linewidth=LINE_WIDTH_PT,
            label=f"{curve.circuit_id}: {curve.name}",
        )
        if show_limits:
            for limit, color in colors.items():
                indices = [index for index, value in enumerate(curve.limit_type) if value == limit]
                if indices:
                    axes.scatter(
                        [curve.lengths_mi[index] for index in indices],
                        [getattr(curve, y)[index] for index in indices],
                        color=color,
                        marker="o",
                        s=18,
                        linewidths=LINE_WIDTH_PT,
                        label=limit.replace("_", " "),
                    )
    axes.set_xlabel("Line length (mi)", fontsize=AXIS_LABEL_SIZE_PT)
    end = "Sending" if y.startswith("ps") else "Receiving"
    axes.set_ylabel(
        f"{end}-end real power (MW)" if y.endswith("mw") else f"{end}-end real power (W)",
        fontsize=AXIS_LABEL_SIZE_PT,
    )
    axes.set_title("St. Clair loadability curve", fontsize=AXIS_TITLE_SIZE_PT)
    axes.tick_params(axis="both", labelsize=TICK_LABEL_SIZE_PT)
    axes.grid(True, alpha=0.3)
    if show_voltage_limit:
        voltage_axes = axes.twinx()
        voltage_axes.set_zorder(axes.get_zorder() - 1)
        axes.set_zorder(voltage_axes.get_zorder() + 1)
        axes.patch.set_visible(False)
        for curve in selected:
            voltage_axes.plot(
                curve.lengths_mi,
                curve.abs_er_pu,
                color="#59636e",
                linestyle=":",
                linewidth=LINE_WIDTH_PT,
                label=f"{curve.circuit_id}: receiving-end voltage",
            )
        voltage_limit = result.options.receiving_voltage_limit_pu
        voltage_axes.axhline(
            voltage_limit,
            color="#d34b3f",
            linestyle="--",
            linewidth=LINE_WIDTH_PT,
            label=f"Voltage-drop limit ({voltage_limit:g} pu)",
        )
        voltage_axes.set_ylabel("Receiving-end voltage (pu)", fontsize=AXIS_LABEL_SIZE_PT)
        voltage_axes.tick_params(axis="y", labelsize=TICK_LABEL_SIZE_PT)
        voltage_axes.grid(False)
        handles, labels = axes.get_legend_handles_labels()
        voltage_handles, voltage_labels = voltage_axes.get_legend_handles_labels()
        unique = dict(zip(labels + voltage_labels, handles + voltage_handles, strict=True))
        axes.legend(
            unique.values(), unique.keys(),
            fontsize=LEGEND_SIZE_PT,
            framealpha=1.0,
        )
    else:
        handles, labels = axes.get_legend_handles_labels()
        unique = dict(zip(labels, handles, strict=True))
        axes.legend(
            unique.values(), unique.keys(),
            fontsize=LEGEND_SIZE_PT,
            framealpha=1.0,
        )
    if show:
        plt.show()
    return axes


__all__ = ["plot_st_clair_curve"]