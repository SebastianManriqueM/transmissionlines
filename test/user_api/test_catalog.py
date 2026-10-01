"""Check catalog discovery through the two-import user API."""

import pandas as pd
import pytest

from transmissionlines.user_api import build


def test_conductor_discovery_preserves_ids_and_75c_measurements() -> None:
    catalog = build.open_catalog()
    choices = catalog.conductors(
        family="ACSS/TW", diameter_min_in=1.0,
        ac_resistance_75c_max_ohm_kft=0.15, ampacity_75c_min_a=900,
    )

    assert choices
    assert all(choice["record_id"] and choice["family"] == "ACSS/TW" for choice in choices)
    assert all(choice["diameter_in"] >= 1.0 for choice in choices)
    assert all(choice["ac_resistance_75c_ohm_kft"] <= 0.15 for choice in choices)
    assert all(choice["ampacity_75c_a"] >= 900 for choice in choices)
    assert [choice["record_id"] for choice in choices] == sorted(
        choice["record_id"] for choice in choices
    )
    assert choices[0]["record_id"] in catalog.format_choices(choices, max_rows=1)
    assert "75 C" in catalog.format_choices(choices, max_rows=1)


def test_v1_ampacity_is_not_advertised_as_75c() -> None:
    catalog = build.open_catalog("data/catalog/v1")

    assert catalog.conductors(ampacity_75c_min_a=1) == []


def test_discovery_bounds_missing_values_and_empty_display() -> None:
    catalog = build.open_catalog()
    assert catalog.conductors(family="nonexistent") == []
    assert catalog.format_choices([]) == "0 matches"
    with pytest.raises(ValueError, match="minimum"):
        catalog.towers(voltage_min_kv=400, voltage_max_kv=200)
    with pytest.raises(ValueError, match="finite"):
        catalog.ground_wires(dc_resistance_max_ohm_kft=float("nan"))
    assert catalog.conductors(gmr_available=True)
    assert not catalog.conductors(family="ACSR", gmr_available=False)
    assert catalog.conductors(family="ACSR", gmr_available=True)
    assert {choice["gmr_method"] for choice in catalog.conductors(family="ACSR")} >= {
        "strand-estimated", "radius-estimated",
    }
    published = next(choice for choice in catalog.conductors(gmr_available=True)
                     if choice["gmr_method"] == "published")
    assert published["gmr_method"] == "published"
    assert "published" in catalog.format_choices([published])
    choices = catalog.ground_wires()
    assert "showing 1" in catalog.format_choices(choices, max_rows=1)
    assert len(choices) > 1


def test_tower_circuits_rejects_duplicate_labels_and_inconsistent_count(monkeypatch) -> None:
    catalog = build.open_catalog()
    geometry_id = catalog.towers(structure_code="3L11")[0]["record_id"]
    original = catalog.repository.table

    def duplicate_phase(table):
        frame = original(table)
        if table == "phase_positions":
            row = frame[frame.geometry_id == geometry_id].iloc[[0]]
            return pd.concat([frame, row], ignore_index=True)
        return frame

    monkeypatch.setattr(catalog.repository, "table", duplicate_phase)
    with pytest.raises(ValueError, match="duplicate phase"):
        catalog.tower_circuits(geometry_id)

    def missing_phase(table):
        frame = original(table)
        if table == "phase_positions":
            target = frame[frame.geometry_id == geometry_id].iloc[0]
            return frame[frame.record_id != target.record_id]
        return frame

    monkeypatch.setattr(catalog.repository, "table", missing_phase)
    with pytest.raises(ValueError, match="exactly A, B, and C"):
        catalog.tower_circuits(geometry_id)


def test_catalog_selection_rejects_ambiguous_ids(monkeypatch) -> None:
    catalog = build.open_catalog()
    original = catalog.repository.table
    record_id = catalog.towers(structure_code="3L11")[0]["record_id"]

    def duplicate_geometry(table):
        frame = original(table)
        if table == "tower_geometries":
            return pd.concat([frame, frame[frame.record_id == record_id]], ignore_index=True)
        return frame

    monkeypatch.setattr(catalog.repository, "table", duplicate_geometry)
    with pytest.raises(ValueError, match="ambiguous"):
        catalog.tower_circuits(record_id)