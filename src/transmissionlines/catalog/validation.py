"""Catalog integrity checks."""

import json
from pathlib import Path

import pandas as pd

from transmissionlines.catalog.importer import sha256_file


def validate_catalog(path: str | Path, *, source_root: str | Path | None = None) -> list[str]:
    """Return integrity errors found in a generated catalog.

    Parameters
    ----------
    path : str or Path
        Catalog directory containing a manifest and Parquet tables.
    source_root : str or Path, optional
        Repository root for checking source PDF and workbook checksums.

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
    is_v2 = manifest.get("catalog_version") == "v2"
    if is_v2 and manifest.get("schema_version") != "4.2.0":
        errors.append("invalid v2 schema version")
    if source_root is not None:
        for source in manifest.get("sources", []):
            source_file = Path(source_root) / source["path"]
            if not source_file.is_file() or sha256_file(source_file) != source["sha256"]:
                errors.append(f"source checksum mismatch: {source['path']}")
    frames: dict[str, pd.DataFrame] = {}
    for table, metadata in manifest.get("tables", {}).items():
        file = root / f"{table}.parquet"
        if not file.exists():
            errors.append(f"missing table {table}")
            continue
        frame = pd.read_parquet(file)
        frames[table] = frame
        if is_v2 and sha256_file(file) != metadata.get("sha256"):
            errors.append(f"table checksum mismatch for {table}")
        if len(frame) != metadata.get("row_count"):
            errors.append(f"row count mismatch for {table}")
        if list(frame.columns) != metadata.get("columns"):
            errors.append(f"column mismatch for {table}")
        if table != "conductor_provenance" and "record_id" in frame and frame["record_id"].duplicated().any():
            errors.append(f"duplicate record_id in {table}")
        if table == "conductor_provenance":
            conductors_file = root / "conductors.parquet"
            if conductors_file.exists() and not set(frame["record_id"]).issubset(
                set(pd.read_parquet(conductors_file, columns=["record_id"])["record_id"])
            ):
                errors.append("orphan conductor provenance")
    if is_v2:
        required = {"conductors", "conductor_provenance", "conductor_issues", "conductor_crosswalk", "sources"}
        if not required.issubset(frames):
            errors.append("missing v2 tables")
        if "conductors" in frames and "conductor_provenance" in frames:
            provenance = frames["conductor_provenance"]
            if not set(provenance["field"]).issubset(set(frames["conductors"].columns)):
                errors.append("invalid conductor provenance field")
        if "sources" in frames and frames["sources"].to_dict("records") != manifest.get("sources"):
            errors.append("sources table does not match manifest")
        if "conductors" in frames and "conductor_crosswalk" in frames:
            crosswalk = frames["conductor_crosswalk"]
            mapped = crosswalk[crosswalk["status"] == "mapped"]
            if not set(mapped["new_record_id"]).issubset(set(frames["conductors"]["record_id"])):
                errors.append("invalid conductor crosswalk target")
            if crosswalk["old_record_id"].duplicated().any():
                errors.append("duplicate conductor crosswalk identity")
    return errors


def require_valid_catalog(path: str | Path, *, source_root: str | Path | None = None) -> None:
    """Raise when catalog integrity validation reports errors.

    Parameters
    ----------
    path : str or Path
        Catalog directory to validate.
    source_root : str or Path, optional
        Repository root to verify source artifacts referenced by the manifest.

    Raises
    ------
    ValueError
        If :func:`validate_catalog` returns one or more integrity errors.
    """
    errors = validate_catalog(path, source_root=source_root)
    if errors:
        raise ValueError("catalog validation failed: " + "; ".join(errors))


__all__ = ["require_valid_catalog", "validate_catalog"]
