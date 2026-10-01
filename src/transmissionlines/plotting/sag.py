"""Plot stored cross-section sag curves without rerunning the solver."""

from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from transmissionlines.models.sag import SagCurveResult
from transmissionlines.plotting.constants import (
    AXIS_LABEL_SIZE_PT,
    AXIS_TITLE_SIZE_PT,
    LEGEND_SIZE_PT,
    LINE_WIDTH_PT,
    SUBTITLE_GAP_PT,
    SUBTITLE_LINE_HEIGHT,
    SUBTITLE_SIZE_PT,
    TICK_LABEL_SIZE_PT,
)


def plot_sag_curve(
    result: SagCurveResult, *, circuit_id: str | None = None, show: bool = False,
) -> Axes:
    """Plot maximum chord-relative sag versus horizontal span.

    Parameters
    ----------
    result : SagCurveResult
        Previously calculated curves; the input graph is not accessed.
    circuit_id : str, optional
        Limit the plot to one configured circuit. By default show all curves.
    show : bool, optional
        Display the figure after plotting when true.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the stored span and sag arrays.

    Raises
    ------
    ValueError
        If the requested circuit is absent from the result.
    """
    selected = [curve for curve in result.curves if circuit_id is None or curve.circuit_id == circuit_id]
    if not selected:
        raise ValueError(f"unknown circuit_id {circuit_id!r} in sag result")
    _, axes = plt.subplots()
    for curve in selected:
        axes.plot(curve.span_lengths_ft, curve.sag_ft, label=curve.circuit_id, linewidth=LINE_WIDTH_PT)
    axes.set_xlabel("Horizontal span (ft)", fontsize=AXIS_LABEL_SIZE_PT)
    axes.set_ylabel("Maximum chord-relative sag (ft)", fontsize=AXIS_LABEL_SIZE_PT)
    descriptions = [
        f"{curve.circuit_id}: {(' '.join(filter(None, (curve.conductor_family, curve.conductor_codeword))) or 'Conductor unspecified')} | {curve.stranding or 'stranding unspecified'}\n"
        f"RTS {curve.rated_strength_lb:g} lbs | weight {curve.weight_lb_kft:g} lbs/kft\n"
        f"Tension {result.everyday_tension_fraction * 100:g}% RTS (H={result.everyday_tension_fraction * curve.rated_strength_lb:g} lbs)"
        for curve in selected if curve.rated_strength_lb is not None and curve.weight_lb_kft is not None
    ]
    if descriptions:
        subtitle = "\n".join(descriptions)
        axes.annotate(
            subtitle, xy=(0.5, 1), xycoords="axes fraction",
            xytext=(0, SUBTITLE_GAP_PT), textcoords="offset points",
            ha="center", va="bottom", fontsize=SUBTITLE_SIZE_PT,
        )
        axes.set_title(
            "Sag curve", fontsize=AXIS_TITLE_SIZE_PT,
            pad=2 * SUBTITLE_GAP_PT + (subtitle.count("\n") + 1) * SUBTITLE_SIZE_PT * SUBTITLE_LINE_HEIGHT,
        )
    else:
        axes.set_title("Sag curve", fontsize=AXIS_TITLE_SIZE_PT)
    axes.tick_params(axis="both", labelsize=TICK_LABEL_SIZE_PT)
    axes.legend(fontsize=LEGEND_SIZE_PT, framealpha=1.0)
    axes.grid(True, alpha=0.3)
    axes.figure.tight_layout()
    if show:
        plt.show()
    return axes