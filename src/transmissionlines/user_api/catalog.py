"""Browse normalized catalog snapshots without implicitly selecting a row."""

import math
from pathlib import Path
from typing import Any

import pandas as pd

from transmissionlines.catalog.repository import CatalogRepository, NoCatalogMatch
from transmissionlines.catalog.schemas import (
    ConductorRecord,
    ConductorV2Record,
    GeometryRecord,
    GroundWireRecord,
)
from transmissionlines.builders.line import conductor_gmr_resolution


def catalog_gmr_available(row: dict[str, Any]) -> bool:
    """Report whether a v2 catalog row has a resolved phase-conductor GMR."""
    normalized = {key: None if pd.isna(value) else value for key, value in row.items()}
    return conductor_gmr_resolution(ConductorV2Record.model_validate(normalized))[1] is not None


def _threshold(value: float | None) -> float | None:
    if value is not None and not math.isfinite(value):
        raise ValueError("numeric filters must be finite")
    return value


def _bounds(minimum: float | None, maximum: float | None) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum filter cannot exceed maximum filter")


def _filter_numeric(
    frame: pd.DataFrame, column: str, *, minimum: float | None = None,
    maximum: float | None = None,
) -> pd.DataFrame:
    minimum, maximum = _threshold(minimum), _threshold(maximum)
    _bounds(minimum, maximum)
    if minimum is not None or maximum is not None:
        values = pd.to_numeric(frame[column], errors="coerce") if column in frame else pd.Series(
            float("nan"), index=frame.index
        )
        if minimum is not None:
            frame = frame[values >= minimum]
        if maximum is not None:
            frame = frame[values <= maximum]
    return frame


def _summary(frame: pd.DataFrame, fields: dict[str, str], version: str) -> list[dict[str, Any]]:
    rows = []
    for _, row in frame.sort_values("record_id").iterrows():
        result: dict[str, Any] = {"record_id": row["record_id"], "catalog_version": version}
        for label, column in fields.items():
            value = row.get(column)
            if label in {"diameter_in", "ac_resistance_75c_ohm_kft", "ampacity_75c_a", "dc_resistance_ohm_kft", "voltage_kv", "gmr", "internal_reactance_ohm_kft"}:
                value = pd.to_numeric(value, errors="coerce")
            result[label] = None if value is None or pd.isna(value) else value
        rows.append(result)
    return rows


class BrowsingCatalog:
    """Browse one snapshot, retaining its exact-selection repository."""

    def __init__(self, path: str | Path, *, catalog_version: str | None = None) -> None:
        self.repository = CatalogRepository(path, catalog_version=catalog_version)
        self.catalog_version = self.repository.catalog_version

    def conductors(
        self, *, family: str | None = None, diameter_min_in: float | None = None,
        diameter_max_in: float | None = None,
        ac_resistance_75c_max_ohm_kft: float | None = None,
        ampacity_75c_min_a: float | None = None, gmr_available: bool | None = None,
    ) -> list[dict[str, Any]]:
        """List phase conductors satisfying exact names and inclusive bounds."""
        frame = self.repository.table("conductors")
        if family is not None:
            frame = frame[frame["family"] == family]
        _bounds(_threshold(diameter_min_in), _threshold(diameter_max_in))
        frame = _filter_numeric(frame, "diameter_inch", minimum=diameter_min_in, maximum=diameter_max_in)
        resistance = "ac_resistance_75c_ohm_kft" if self.catalog_version == "v2" else "_unrated"
        ampacity = "ampacity_75c_a" if self.catalog_version == "v2" else "_unrated"
        frame = _filter_numeric(frame, resistance, maximum=ac_resistance_75c_max_ohm_kft)
        frame = _filter_numeric(frame, ampacity, minimum=ampacity_75c_min_a)
        model = ConductorV2Record if self.catalog_version == "v2" else ConductorRecord
        methods = {
            row["record_id"]: conductor_gmr_resolution(model.model_validate({
                key: None if pd.isna(value) else value for key, value in row.items()
            }))[0]
            for _, row in frame.iterrows()
        }
        if gmr_available is not None:
            available = frame["record_id"].map(lambda record_id: methods[record_id] != "missing")
            frame = frame[available == gmr_available]
        choices = _summary(frame, {
            "family": "family", "codeword": "codeword", "diameter_in": "diameter_inch",
            "ac_resistance_75c_ohm_kft": resistance, "ampacity_75c_a": ampacity,
            "gmr": "gmr_ft", "internal_reactance_ohm_kft": "internal_reactance_ohm_kft",
        }, self.catalog_version)
        for choice in choices:
            choice["gmr_method"] = methods[choice["record_id"]]
        return choices

    def ground_wires(
        self, *, family: str | None = None, diameter_min_in: float | None = None,
        diameter_max_in: float | None = None, dc_resistance_max_ohm_kft: float | None = None,
    ) -> list[dict[str, Any]]:
        """List ground wires satisfying exact names and inclusive bounds."""
        frame = self.repository.table("ground_wires")
        if family is not None:
            frame = frame[frame["family"] == family]
        _bounds(_threshold(diameter_min_in), _threshold(diameter_max_in))
        frame = _filter_numeric(frame, "diameter_inch", minimum=diameter_min_in, maximum=diameter_max_in)
        frame = _filter_numeric(frame, "dc_resistance_ohm_kft", maximum=dc_resistance_max_ohm_kft)
        return _summary(frame, {
            "family": "family", "size": "awg_or_stranding", "diameter_in": "diameter_inch",
            "dc_resistance_ohm_kft": "dc_resistance_ohm_kft",
        }, self.catalog_version)

    def towers(
        self, *, structure_type: str | None = None, n_circuits: int | None = None,
        n_ground_wires: int | None = None, voltage_min_kv: float | None = None,
        voltage_max_kv: float | None = None, structure_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tower geometries satisfying exact names and inclusive bounds."""
        frame = self.repository.table("tower_geometries")
        for column, value in (
            ("structure_type", structure_type), ("structure_code", structure_code),
            ("n_circuits", n_circuits), ("n_ground_w", n_ground_wires),
        ):
            if value is not None:
                frame = frame[frame[column] == value]
        _bounds(_threshold(voltage_min_kv), _threshold(voltage_max_kv))
        frame = _filter_numeric(frame, "voltage_kv", minimum=voltage_min_kv, maximum=voltage_max_kv)
        return _summary(frame, {
            "structure_code": "structure_code", "structure_type": "structure_type",
            "voltage_kv": "voltage_kv", "n_circuits": "n_circuits", "n_ground_wires": "n_ground_w",
        }, self.catalog_version)

    def select(self, table: str, record_id: str) -> ConductorRecord | GeometryRecord | GroundWireRecord:
        """Validate one explicitly selected equipment or geometry record."""
        row = self.repository.select_exact(table, record_id=record_id)
        model = {
            "conductors": ConductorV2Record if self.catalog_version == "v2" else ConductorRecord,
            "tower_geometries": GeometryRecord, "ground_wires": GroundWireRecord,
        }[table]
        return model.model_validate(row)

    def positions(self, table: str, geometry_id: str) -> list[dict[str, Any]]:
        """Read all positions joined to an explicitly selected geometry ID."""
        frame = self.repository.table(table)
        return frame[frame["geometry_id"] == geometry_id].to_dict("records")

    def tower_circuits(self, geometry_id: str) -> tuple[str, ...]:
        """Return actual circuit IDs after validating geometry phase positions."""
        geometry = self.select("tower_geometries", geometry_id)
        positions = self.positions("phase_positions", geometry_id)
        if not positions:
            raise NoCatalogMatch(f"geometry {geometry_id!r} has no phase positions")
        labels = [(position["circuit_id"], position["phase"]) for position in positions]
        if len(set(labels)) != len(labels):
            raise ValueError(f"geometry {geometry_id!r} has duplicate phase labels")
        circuits = tuple(sorted({circuit for circuit, _ in labels}))
        if any({phase for circuit_id, phase in labels if circuit_id == circuit} != {"A", "B", "C"} for circuit in circuits):
            raise ValueError(f"geometry {geometry_id!r}: each circuit needs exactly A, B, and C phases")
        if geometry.n_circuits is not None and len(circuits) != geometry.n_circuits:
            raise ValueError(f"geometry {geometry_id!r} circuit count disagrees with phase positions")
        return circuits

    def format_choices(self, choices: list[dict[str, Any]], *, max_rows: int = 20) -> str:
        """Format a bounded preview without truncating IDs or query results."""
        if max_rows < 0:
            raise ValueError("max_rows must be nonnegative")
        if not choices:
            return "0 matches"
        columns = [key for key in choices[0] if key not in ("catalog_version", "gmr", "internal_reactance_ohm_kft")]
        labels = {
            "ac_resistance_75c_ohm_kft": "AC resistance 75 C (ohm/kft)",
            "ampacity_75c_a": "Ampacity 75 C (A)", "diameter_in": "Diameter (in)",
            "dc_resistance_ohm_kft": "DC resistance (ohm/kft)", "voltage_kv": "Voltage (kV)",
        }
        values = [[str(labels.get(key, key)) for key in columns]]
        for choice in choices[:max_rows]:
            values.append([str(
                choice.get(key) if choice.get(key) is not None else "-"
            ) for key in columns])
        widths = [max(len(row[index]) for row in values) for index in range(len(columns))]
        lines = [f"{len(choices)} matches" + (f" (showing {max_rows})" if len(choices) > max_rows else "")]
        lines.extend("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in values)
        return "\n".join(lines)