"""Base for transient calculation results outside the Infrasys system."""

from pydantic import BaseModel, ConfigDict


class CalculationResultModel(BaseModel):
    """Keep calculated outputs frozen without component registration fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)