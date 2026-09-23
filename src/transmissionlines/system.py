"""Provide the versioned infrasys system for transmission-line components."""

import json
from pathlib import Path
from typing import Any, ClassVar, cast

from infrasys import System


class TransmissionLineSystem(System):
    """Persist a transmission-line component graph with package schema metadata."""

    schema_version: ClassVar[str] = "0.1"
    _schema_version_key: ClassVar[str] = "transmissionlines_schema_version"

    def serialize_system_attributes(self) -> dict[str, Any]:
        """Serialize the package schema version at the JSON root."""
        return {self._schema_version_key: self.schema_version}

    def deserialize_system_attributes(self, data: dict[str, Any]) -> None:
        """Validate package schema metadata while restoring a system."""
        self._validate_schema_version(data.get(self._schema_version_key))

    @classmethod
    def from_json(
        cls,
        filename: Path | str,
        upgrade_handler: Any | None = None,
        **kwargs: Any,
    ) -> "TransmissionLineSystem":
        """Restore a supported package schema from an infrasys JSON file."""
        path = Path(filename)
        data = json.loads(path.read_text(encoding="utf-8"))
        cls._validate_schema_version(data.get(cls._schema_version_key))
        return cast(
            TransmissionLineSystem,
            super().from_json(path, upgrade_handler=upgrade_handler, **kwargs),
        )

    @classmethod
    def _validate_schema_version(cls, version: object) -> None:
        """Reject missing or unsupported package schema versions."""
        if version != cls.schema_version:
            raise ValueError(
                "Unsupported transmissionlines schema version: "
                f"{version!r}; expected {cls.schema_version!r}"
            )