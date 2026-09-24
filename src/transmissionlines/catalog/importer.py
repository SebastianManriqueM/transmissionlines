"""Reproducible source-to-Parquet catalog generation."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from transmissionlines.catalog.schemas import SOURCE_HEADERS, TABLE_MODELS


def sha256_file(path: str | Path) -> str:
    """Return SHA-256 of an unchanged source artifact."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xls", ".xlsx"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def generate_catalog(
    raw_sources: Mapping[str, str | Path],
    output: str | Path,
    *,
    catalog_version: str = "v1",
    schema_version: str = "3.0.0",
    header_mappings: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Normalize explicitly mapped source headers and write deterministic Parquet tables.

    Parameters
    ----------
    raw_sources : Mapping[str, str | Path]
        Mapping of normalized table name to source artifact.
    output : str | Path
        Destination version directory.
    catalog_version, schema_version : str
        Manifest version labels.
    header_mappings : Mapping, optional
        Normalized-column to source-header mappings. Missing mappings are rejected.
    """
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    mappings = header_mappings or SOURCE_HEADERS
    tables: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    for table, source in raw_sources.items():
        path = Path(source)
        frame = _read(path)
        mapping = mappings.get(table, {})
        model = TABLE_MODELS.get(table)
        if model is None:
            raise ValueError(f"unsupported catalog table {table!r}")
        expected = set(model.model_fields)
        if set(mapping) != expected:
            missing = sorted(expected - set(mapping))
            extra = sorted(set(mapping) - expected)
            raise ValueError(
                f"incomplete mapping for {table}: missing={missing}, extra={extra}"
            )
        missing_headers = [source_name for source_name in mapping.values() if source_name not in frame.columns]
        if missing_headers:
            raise ValueError(f"source {path} is missing mapped headers: {missing_headers}")
        normalized = frame.rename(
            columns={source_name: name for name, source_name in mapping.items()}
        )[list(model.model_fields)]
        records = []
        failures = []
        for index, row in normalized.iterrows():
            values = {key: (None if pd.isna(value) else value) for key, value in row.to_dict().items()}
            try:
                records.append(model.model_validate(values).model_dump())
            except Exception as exc:
                failures.append(f"row {index}: {exc}")
        if failures:
            raise ValueError(f"invalid {table} records: " + "; ".join(failures[:10]))
        normalized = pd.DataFrame(records, columns=list(model.model_fields))
        normalized.to_parquet(
            destination / f"{table}.parquet", index=False, engine="pyarrow", compression="snappy"
        )
        tables[table] = {"row_count": len(normalized), "columns": list(normalized.columns)}
        sources.append({"path": str(path), "sha256": sha256_file(path)})
    manifest = {
        "catalog_version": catalog_version,
        "schema_version": schema_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": sources,
        "tables": tables,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


__all__ = ["generate_catalog", "sha256_file"]
