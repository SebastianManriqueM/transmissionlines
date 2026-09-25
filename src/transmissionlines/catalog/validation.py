"""Catalog integrity checks."""

import json
from pathlib import Path

import pandas as pd


def validate_catalog(path: str | Path) -> list[str]:
    """Return integrity errors found in a generated catalog.

    Parameters
    ----------
    path : str or Path
        Catalog directory containing a manifest and Parquet tables.

    Returns
    -------
    list of str
        Missing-file, row-count, column-order, and duplicate-ID errors. An
        empty list indicates that these integrity checks passed.
    """
    root = Path(path)
    errors: list[str] = []
    manifest_file = root / "manifest.json"
    if not manifest_file.exists():
        return ["manifest.json is missing"]
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    for table, metadata in manifest.get("tables", {}).items():
        file = root / f"{table}.parquet"
        if not file.exists():
            errors.append(f"missing table {table}")
            continue
        frame = pd.read_parquet(file)
        if len(frame) != metadata.get("row_count"):
            errors.append(f"row count mismatch for {table}")
        if list(frame.columns) != metadata.get("columns"):
            errors.append(f"column mismatch for {table}")
        if "record_id" in frame and frame["record_id"].duplicated().any():
            errors.append(f"duplicate record_id in {table}")
    return errors


def require_valid_catalog(path: str | Path) -> None:
    """Raise when catalog integrity validation reports errors.

    Parameters
    ----------
    path : str or Path
        Catalog directory to validate.

    Raises
    ------
    ValueError
        If :func:`validate_catalog` returns one or more integrity errors.
    """
    errors = validate_catalog(path)
    if errors:
        raise ValueError("catalog validation failed: " + "; ".join(errors))


__all__ = ["require_valid_catalog", "validate_catalog"]
