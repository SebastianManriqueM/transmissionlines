"""Standalone typed results that are never registered in Infrasys."""

from uuid import UUID

from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.result_base import CalculationResultModel
from transmissionlines.models.st_clair import StClairResult


class LineCalculationResult(CalculationResultModel):
    """Identify the selected cross-section and its transient calculated outputs."""

    line_name: str
    line_uuid: UUID
    configuration_uuid: UUID
    electrical: ElectricalParameters
    st_clair: StClairResult | None = None


__all__ = ["CalculationResultModel", "LineCalculationResult"]