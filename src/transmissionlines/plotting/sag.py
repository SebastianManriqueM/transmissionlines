"""Plot stored cross-section sag curves without rerunning the solver."""

from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from transmissionlines.models.sag import SagCurveResult


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
        axes.plot(curve.span_lengths_ft, curve.sag_ft, label=curve.circuit_id)
    axes.set_xlabel("Horizontal span (ft)")
    axes.set_ylabel("Maximum chord-relative sag (ft)")
    axes.legend()
    axes.grid(True, alpha=0.3)
    if show:
        plt.show()
    return axes