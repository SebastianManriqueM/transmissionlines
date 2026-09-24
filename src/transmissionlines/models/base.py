"""Shared base models for transmission-line data."""

from abc import ABC
from typing import Any

from infrasys import BaseQuantity, SupplementalAttribute
from infrasys.serialization import (
    TYPE_METADATA,
    SerializedQuantityType,
    SerializedType,
    SerializedTypeMetadata,
)
from pydantic import BaseModel, ConfigDict, model_serializer, model_validator


class LineDataModel(BaseModel):
    """Base class for immutable embedded transmission-line value models.

    Value models are serialized by value inside registered Infrasys components or
    supplemental attributes. They intentionally have no UUID, system identity, or
    component name.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _deserialize_embedded_quantities(cls, data: Any) -> Any:
        """Restore Infrasys quantity dictionaries before field validation.

        Parameters
        ----------
        data : Any
            Raw Pydantic input for a value model.

        Returns
        -------
        Any
            Input with serialized quantity dictionaries converted back to quantity objects.
        """
        return _restore_embedded_quantities(data)

    @model_serializer(mode="plain")
    def _serialize_embedded_quantities(self) -> dict[str, Any]:
        """Serialize nested Infrasys quantities with explicit type metadata.

        Returns
        -------
        dict[str, Any]
            JSON-compatible representation of this embedded value model.
        """
        return {
            field: _dump_embedded_value(getattr(self, field))
            for field in type(self).model_fields
        }


def _dump_embedded_value(value: Any) -> Any:
    """Return a JSON-compatible embedded value representation."""
    if isinstance(value, BaseQuantity):
        data = value.to_dict()
        data[TYPE_METADATA] = SerializedTypeMetadata.validate_python(
            SerializedQuantityType(module=value.__module__, type=value.__class__.__name__)
        ).model_dump()
        return data
    if isinstance(value, LineDataModel):
        return value._serialize_embedded_quantities()
    if isinstance(value, list):
        return [_dump_embedded_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_dump_embedded_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _dump_embedded_value(item) for key, item in value.items()}
    return value


def _restore_embedded_quantities(value: Any) -> Any:
    """Return input with serialized Infrasys quantity values restored."""
    if isinstance(value, dict):
        metadata = value.get(TYPE_METADATA)
        if metadata and metadata.get("serialized_type") == SerializedType.QUANTITY.value:
            quantity_metadata = SerializedTypeMetadata.validate_python(metadata)
            quantity_type = __import__(
                quantity_metadata.module,
                fromlist=[quantity_metadata.type],
            )
            quantity_class = getattr(quantity_type, quantity_metadata.type)
            return quantity_class.from_dict(value)
        return {key: _restore_embedded_quantities(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_embedded_quantities(item) for item in value]
    return value


class OperationAttribute(SupplementalAttribute, ABC):
    """Common base for operational supplemental attributes.

    Operational attributes keep Infrasys supplemental-attribute identity and time-series
    ownership behavior without requiring component names.
    """
