"""Read-only exact catalog repository."""

import json
from pathlib import Path
from typing import Any

import pandas as pd


class CatalogSelectionError(ValueError):
    """Base class for deterministic selection failures."""


class NoCatalogMatch(CatalogSelectionError):
    """No exact record matched a selector."""


class AmbiguousCatalogMatch(CatalogSelectionError):
    """More than one exact record matched a selector."""


class CatalogRepository:
    """Query normalized Parquet tables without exposing raw source rows."""

    def __init__(self, path: str | Path, *, catalog_version: str | None = None) -> None:
        self.path = Path(path)
        manifest_path = self.path / "manifest.json"
        self.manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        )
        self.catalog_version = catalog_version or self.manifest.get("catalog_version")

    def table(self, name: str) -> pd.DataFrame:
        """Load one named normalized table."""
        if not name.replace("_", "").isalnum():
            raise ValueError("invalid table name")
        file = self.path / f"{name}.parquet"
        if not file.exists():
            raise FileNotFoundError(file)
        return pd.read_parquet(file)

    def select_exact(self, table: str, **selectors: Any) -> dict[str, Any]:
        """Return exactly one record using equality joins only."""
        frame = self.table(table)
        for key, value in selectors.items():
            if key not in frame.columns:
                raise NoCatalogMatch(f"unknown selector {key!r} for {table}")
            frame = frame[frame[key] == value]
        if frame.empty:
            raise NoCatalogMatch(f"no exact {table} record matches {selectors}")
        if len(frame) != 1:
            raise AmbiguousCatalogMatch(f"ambiguous {table} selection for {selectors}")
        return frame.iloc[0].to_dict()

    def select_state(self, selector: str) -> dict[str, Any]:
        """Select one state by exact FIPS, USPS, or canonical name."""
        frame = self.table("states")
        matches = frame[
            (frame["code"] == selector)
            | (frame["usps_code"] == selector)
            | (frame["canonical_name"] == selector)
        ]
        if len(matches) == 0:
            raise NoCatalogMatch(f"no exact state matches {selector!r}")
        if len(matches) != 1:
            raise AmbiguousCatalogMatch(f"ambiguous state selector {selector!r}")
        return matches.iloc[0].to_dict()


__all__ = ["AmbiguousCatalogMatch", "CatalogRepository", "CatalogSelectionError", "NoCatalogMatch"]
