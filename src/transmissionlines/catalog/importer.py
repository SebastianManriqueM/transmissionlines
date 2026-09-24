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




def generate_julia_workbook_catalog(
    workbook: str | Path,
    output: str | Path,
    *,
    catalog_version: str = "v1",
    schema_version: str = "3.0.0",
) -> dict[str, Any]:
    """Normalize the original ``Tower_geometries_DB.xlsx`` into the v3 catalog.

    The workbook is treated as an immutable raw source.  This adapter is the
    only place where its legacy column positions/names are interpreted.
    """
    path = Path(workbook)
    geometry = pd.read_excel(path, sheet_name="TL_Geometry")
    neighboring = pd.read_excel(path, sheet_name="Neighboring")
    dataset = pd.read_excel(path, sheet_name="TL_dataset")
    conductors = pd.read_excel(path, sheet_name="Conductors")
    wires = pd.read_excel(path, sheet_name="G_wire")

    def clean(value: Any) -> Any:
        return None if pd.isna(value) else value

    def records(table: str, rows: list[dict[str, Any]]) -> pd.DataFrame:
        model = TABLE_MODELS[table]
        validated = [model.model_validate(row).model_dump() for row in rows]
        return pd.DataFrame(validated, columns=list(model.model_fields))

    geometry_rows = [{"record_id": str(row.code), "source_id": str(row.code), "structure_code": str(row.code), "structure_type": clean(row.structure_type), "company": clean(row.company), "state": clean(row.state), "voltage_kv": clean(row.voltage_kv), "n_circuits": clean(row.n_circuits), "n_ground_w": clean(row.n_ground_w)} for row in geometry.itertuples()]
    phase_rows: list[dict[str, Any]] = []
    ground_rows: list[dict[str, Any]] = []
    for row in geometry.itertuples():
        code = str(row.code)
        for circuit in (1, 2):
            if circuit == 2 and clean(row.n_circuits) != 2:
                continue
            for phase, y_name, x_name in (("A", f"ha{circuit}t_ft", f"Sa{circuit}t_ft"), ("B", f"hb{circuit}t_ft", f"Sb{circuit}t_ft"), ("C", f"hc{circuit}t_ft", f"Sc{circuit}t_ft")):
                y, x = clean(getattr(row, y_name)), clean(getattr(row, x_name))
                if y is not None and x is not None:
                    phase_rows.append({"record_id": f"{code}:circuit-{circuit}:{phase}", "source_id": code, "geometry_id": code, "state_id": clean(row.state), "circuit_id": f"circuit-{circuit}", "phase": phase, "x": x, "y": y})
        for wire, y_name, x_name in ((1, "hg11t_ft", "Sg11t_ft"), (2, "hg21t_ft", "Sg21t_ft")):
            y, x = clean(getattr(row, y_name)), clean(getattr(row, x_name))
            if y is not None and x is not None and wire <= int(clean(row.n_ground_w) or 0):
                ground_rows.append({"record_id": f"{code}:ground-{wire}", "source_id": code, "geometry_id": code, "state_id": clean(row.state), "wire_id": f"ground-{wire}", "x": x, "y": y})
    state_rows = [{"record_id": str(clean(row.abreviation) or row.state), "source_id": str(row.number), "code": str(clean(row.abreviation) or row.state), "usps_code": clean(row.abreviation), "canonical_name": str(row.state)} for row in neighboring.itertuples()]
    border_rows = []
    state_code = {str(row.state): str(row.abreviation or row.state) for row in neighboring.itertuples()}
    for row in neighboring.itertuples():
        for neighbor in str(row.bordering_states).split(","):
            if neighbor.strip() in state_code:
                border_rows.append({"record_id": f"{state_code[str(row.state)]}:{state_code[neighbor.strip()]}", "source_id": str(row.number), "state_code": state_code[str(row.state)], "border_state_code": state_code[neighbor.strip()]})
    conductor_rows = []
    for index, row in enumerate(conductors.itertuples(), 1):
        conductor_rows.append({"record_id": f"{row.type}:{row.codeword}:{row.size_kcmil}:{index}", "source_id": str(row.codeword), "family": str(row.type), "codeword": str(row.codeword), "stranding": clean(row.stranding), "size_kcmil": clean(row.size_kcmil), "diameter_inch": clean(row.diameter_inch), "ac_resistance_ohm_kft": clean(row.R_75AC_ohm_kft), "ac_resistance_25_ohm_kft": clean(row.R_25AC_ohm_kft), "ac_resistance_50_ohm_kft": clean(row.R_50AC_ohm_kft), "ac_resistance_75_ohm_kft": clean(row.R_75AC_ohm_kft), "dc_resistance_ohm_kft": clean(row.R_20dc_ohm_kft), "capacitance_reactance_mohm_kft": clean(row.C_60Hz_Mohm_kft), "internal_reactance_ohm_kft": clean(row.L_60Hz_ohm_kft), "ampacity_a": clean(row.ampacity_a)})
    wire_rows = [{"record_id": f"{row.type}:{row.awg}:{row.size_kcmil}:{index}", "source_id": str(row.awg), "family": str(row.type), "awg_or_stranding": str(row.awg), "size_kcmil": clean(row.size_kcmil), "strand_diameter_inch": clean(row.wire_diameter_inch), "diameter_inch": clean(row.diameter_inch), "dc_resistance_ohm_kft": clean(row.R_20dc_ohm_kft), "breaking_load_lb": clean(row.breaking_load_lb), "weight_lb_kft": clean(row.weight_lb_kft), "area_inches": clean(row.area_inches)} for index, row in enumerate(wires.itertuples(), 1)]
    actual_rows = [{"record_id": str(i), "source_id": "TL_dataset", "structure_code": clean(row.code), "structure_type": clean(row.structure_type), "state_id": clean(row.state), "miles": clean(row.miles), "voltage_kv": clean(row.voltage_kv)} for i, row in enumerate(dataset.itertuples(), 1)]
    frames = {"tower_geometries": records("tower_geometries", geometry_rows), "phase_positions": records("phase_positions", phase_rows), "ground_wire_positions": records("ground_wire_positions", ground_rows), "states": records("states", state_rows), "state_borders": records("state_borders", border_rows), "conductors": records("conductors", conductor_rows), "ground_wires": records("ground_wires", wire_rows), "actual_lines": records("actual_lines", actual_rows)}
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    table_info: dict[str, Any] = {}
    for name, frame in frames.items():
        frame.to_parquet(destination / f"{name}.parquet", index=False, engine="pyarrow", compression="snappy")
        table_info[name] = {"row_count": len(frame), "columns": list(frame.columns)}
    manifest = {"catalog_version": catalog_version, "schema_version": schema_version, "generated_at": datetime.now(UTC).isoformat(), "sources": [{"path": str(path), "sha256": sha256_file(path)}], "tables": table_info, "source_workbook": "Tower_geometries_DB.xlsx"}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


__all__ = ["generate_catalog", "generate_julia_workbook_catalog", "sha256_file"]
