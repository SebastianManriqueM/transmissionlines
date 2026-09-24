"""Transmission-line system runtime foundation."""

from typing import Any

from infrasys import System
from infrasys.exceptions import ISOperationNotAllowed

SCHEMA_VERSION = "3.0.0"
"""Current transmission-line system schema version."""

_LEGACY_SCHEMA_VERSIONS = {None, "2.0.0", SCHEMA_VERSION}


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
        """Resolve component references nested in v3 value models after deserialization.

        Infrasys preserves UUIDs for nested references but does not automatically
        replace nested copies with the registered component instances.
        """
        from transmissionlines.models.assets import TransmissionLine

        for line in self.get_components(TransmissionLine):
            resolved = line.resolve_component_references(self)
            if resolved is not line:
                self.remove_component(line)
                self.add_component(resolved)

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
        upgrade_transmissionlines_system_data(
            data,
            from_version=data.get("data_format_version"),
            to_version=SCHEMA_VERSION,
        )
        self._schema_version = data["transmissionlines_schema_version"]
        self.data_format_version = data["data_format_version"]

    def handle_data_format_upgrade(
        self,
        data: dict[str, Any],
        from_version: str | None,
        to_version: str | None,
    ) -> None:
        """Upgrade legacy transmission-line system metadata in place.

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
        upgrade_transmissionlines_system_data(
            data,
            from_version=from_version,
            to_version=to_version,
        )


def upgrade_transmissionlines_system_data(
    data: dict[str, Any],
    *,
    from_version: str | None,
    to_version: str | None,
) -> None:
    """Upgrade serialized transmission-line schema metadata in place.

    Parameters
    ----------
    data : dict[str, Any]
        System JSON dictionary to update.
    from_version : str | None
        Existing Infrasys data-format version value.
    to_version : str | None
        Target data-format version value.

    Raises
    ------
    ISOperationNotAllowed
        Raised when no compatible metadata-only upgrade path exists.
    """
    target_version = to_version or SCHEMA_VERSION
    if from_version not in _LEGACY_SCHEMA_VERSIONS:
        msg = (
            "Unsupported Infrasys data format upgrade: "
            f"{from_version!r} -> {target_version!r}"
        )
        raise ISOperationNotAllowed(msg)

    package_version = data.get("transmissionlines_schema_version")
    if package_version not in _LEGACY_SCHEMA_VERSIONS:
        msg = f"Unsupported transmission-line package schema: {package_version!r}"
        raise ISOperationNotAllowed(msg)

    _migrate_legacy_matrix_payloads(data)
    data["data_format_version"] = target_version
    data["transmissionlines_schema_version"] = target_version


def _migrate_legacy_matrix_payloads(value: Any) -> None:
    """Convert legacy cell-list matrices to typed JSON matrix payloads in place."""
    if isinstance(value, list):
        for item in value:
            _migrate_legacy_matrix_payloads(item)
        return
    if not isinstance(value, dict):
        return
    for item in value.values():
        _migrate_legacy_matrix_payloads(item)
    matrices = value.get("matrices")
    if not isinstance(matrices, dict):
        return
    raw_labels = value.get("labels")
    labels: list[str] = [str(item) for item in raw_labels] if isinstance(raw_labels, list) else []
    raw_units = value.get("units")
    units: dict[str, Any] = raw_units if isinstance(raw_units, dict) else {}
    migrated = False
    for name, matrix in list(matrices.items()):
        if not isinstance(matrix, list) or not matrix or not isinstance(matrix[0], list):
            continue
        rows = len(matrix)
        columns = len(matrix[0])
        real: list[list[float]] = []
        imaginary: list[list[float]] = []
        for row in matrix:
            real_row: list[float] = []
            imaginary_row: list[float] = []
            for cell in row:
                if isinstance(cell, dict):
                    real_row.append(float(cell.get("real", 0.0)))
                    imaginary_row.append(float(cell.get("imag", 0.0)))
                else:
                    real_row.append(float(cell))
                    imaginary_row.append(0.0)
            real.append(real_row)
            imaginary.append(imaginary_row)
        matrix_labels = labels if len(labels) == rows else [str(index) for index in range(rows)]
        unit = units.get("y" if name.startswith("Y") else "z", "")
        matrices[name] = {
            "name": name,
            "row_count": rows,
            "column_count": columns,
            "row_labels": matrix_labels,
            "column_labels": list(matrix_labels) if len(matrix_labels) == columns else [str(index) for index in range(columns)],
            "unit": unit,
            "real": real,
            "imaginary": imaginary,
        }
        migrated = True
    if migrated and value.get("status") == "complete":
        value["status"] = "incomplete"


__all__ = [
    "SCHEMA_VERSION",
    "TransmissionLineSystem",
    "upgrade_transmissionlines_system_data",
]
