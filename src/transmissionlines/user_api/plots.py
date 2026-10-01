"""Plot stored cross-section calculation results."""

from matplotlib.axes import Axes

from transmissionlines.models.sag import SagCurveResult
from transmissionlines.models.st_clair import StClairResult
from transmissionlines.plotting.sag import plot_sag_curve
from transmissionlines.plotting.st_clair import plot_st_clair_curve


def st_clair(result: StClairResult) -> Axes:
	"""Plot an existing St. Clair curve and return its axes."""
	return plot_st_clair_curve(result)


def sag(result: SagCurveResult, *, circuit_id: str | None = None) -> Axes:
	"""Plot stored sag curves, optionally selecting one circuit."""
	return plot_sag_curve(result, circuit_id=circuit_id)