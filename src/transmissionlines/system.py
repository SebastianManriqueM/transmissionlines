"""Transmission-line system runtime foundation."""

from typing import Any

from infrasys import System
from infrasys.exceptions import ISOperationNotAllowed

SCHEMA_VERSION = "4.0.0"
"""Current transmission-line system schema version."""


class TransmissionLineSystem(System):
    """Infrasys system configured for transmission-line model data.

    Parameters
    ----------
    name : str | None
        Optional system name.
    description : str | None
        Optional system description.
    **kwargs : Any
        Additional keyword arguments forwarded to :class:`infrasys.System`, such as
        time-series storage options.
    """

    def __init__(
        self,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, description=description, **kwargs)
        self.data_format_version = SCHEMA_VERSION
        self._schema_version = SCHEMA_VERSION

    def resolve_component_references(self) -> None:
        """Keep the Infrasys reference-resolution hook for direct component fields."""

    @property
    def schema_version(self) -> str:
        """Return the transmission-line schema version for this system."""
        return self._schema_version

    def serialize_system_attributes(self) -> dict[str, Any]:
        """Serialize transmission-line root-level metadata.

        Returns
        -------
        dict[str, Any]
            Extra root-level metadata merged into the Infrasys JSON document.
        """
        return {"transmissionlines_schema_version": self.schema_version}

    def deserialize_system_attributes(self, data: dict[str, Any]) -> None:
        """Deserialize transmission-line root-level metadata.

        Parameters
        ----------
        data : dict[str, Any]
            System JSON dictionary after any schema upgrade hook has run.
        """
        if data.get("transmissionlines_schema_version") != SCHEMA_VERSION:
            raise ISOperationNotAllowed("Unsupported transmission-line package schema")
        self._schema_version = data["transmissionlines_schema_version"]
        self.data_format_version = data["data_format_version"]

    def handle_data_format_upgrade(
        self,
        data: dict[str, Any],
        from_version: str | None,
        to_version: str | None,
    ) -> None:
        """Reject unsupported legacy system formats.

        Parameters
        ----------
        data : dict[str, Any]
            System JSON dictionary that will be deserialized by Infrasys.
        from_version : str | None
            Version recorded in the serialized system.
        to_version : str | None
            Target version requested by the runtime.

        Raises
        ------
        ISOperationNotAllowed
            Raised when the serialized version is not supported by this foundation slice.
        """
        raise ISOperationNotAllowed("Unsupported transmission-line system data format")


__all__ = [
    "SCHEMA_VERSION",
    "TransmissionLineSystem",
]
