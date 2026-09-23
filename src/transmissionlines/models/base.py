"""Define base classes for transmission-line values and system objects."""

from abc import ABC
from typing import Any

from infrasys import BaseQuantity, Component, SupplementalAttribute
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator


class LineDataModel(BaseModel):
    """Represent frozen nested data owned by a line component."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def parse_quantity_strings(cls, value: Any, info: ValidationInfo) -> Any:
        """Restore serialized quantities using their declared semantic type."""
        if info.field_name is None:
            return value
        annotation = cls.model_fields[info.field_name].annotation
        if (
            isinstance(value, str)
            and isinstance(annotation, type)
            and issubclass(annotation, BaseQuantity)
        ):
            parsed = BaseQuantity._REGISTRY.Quantity(value)
            return annotation(parsed.magnitude, parsed.units)
        return value


class LineComponent(Component, ABC):
    """Represent an abstract named component in a line system."""


class LineAssetComponent(LineComponent, ABC):
    """Represent an abstract physical or topological line asset."""


class LineConfigurationComponent(LineComponent, ABC):
    """Represent an abstract named static line configuration."""


class OperationAttribute(SupplementalAttribute, ABC):
    """Represent an abstract operational supplemental attribute."""