"""Shared base models for transmission-line data."""

from abc import ABC

from infrasys import SupplementalAttribute
from pydantic import BaseModel, ConfigDict


class LineDataModel(BaseModel):
    """Base class for immutable embedded transmission-line value models.

    Value models are serialized by value inside registered Infrasys components or
    supplemental attributes. They intentionally have no UUID, system identity, or
    component name.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class OperationAttribute(SupplementalAttribute, ABC):
    """Common base for operational supplemental attributes.

    Operational attributes keep Infrasys supplemental-attribute identity and time-series
    ownership behavior without requiring component names.
    """
