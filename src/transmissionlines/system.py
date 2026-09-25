"""Infrasys system runtime for canonical transmission-line components."""

from typing import Any

from infrasys import System

SCHEMA_VERSION = "4.0.0"


class TransmissionLineSystem(System):
    """Infrasys system configured for canonical transmission-line data."""

    def __init__(self, name: str | None = None, description: str | None = None, **kwargs: Any) -> None:
        super().__init__(name=name, description=description, **kwargs)
        self.data_format_version = SCHEMA_VERSION
        self._schema_version = SCHEMA_VERSION

    @property
    def schema_version(self) -> str:
        """Return the current transmission-line schema version."""
        return self._schema_version

    def serialize_system_attributes(self) -> dict[str, Any]:
        """Serialize canonical package metadata."""
        return {"transmissionlines_schema_version": self.schema_version}

    def deserialize_system_attributes(self, data: dict[str, Any]) -> None:
        """Restore canonical package metadata."""
        self._schema_version = data.get("transmissionlines_schema_version", SCHEMA_VERSION)
        self.data_format_version = data.get("data_format_version", SCHEMA_VERSION)


__all__ = ["SCHEMA_VERSION", "TransmissionLineSystem"]
