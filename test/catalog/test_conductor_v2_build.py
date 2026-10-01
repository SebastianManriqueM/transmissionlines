"""Check reproducible PDF-backed v2 catalog publication."""

import json
from pathlib import Path

import pandas as pd
import pytest

from transmissionlines.catalog.conductor_v2_build import build_conductor_catalog
from transmissionlines.catalog.repository import AmbiguousCatalogMatch, CatalogRepository
from transmissionlines.catalog.validation import validate_catalog


ROOT = Path(__file__).resolve().parents[2]


def test_build_v2_preserves_v1_and_publishes_auditable_conductors(tmp_path: Path) -> None:
    v1 = ROOT / "data/catalog/v1"
    original = {file.name: file.read_bytes() for file in v1.iterdir() if file.is_file()}
    output = tmp_path / "v2"

    manifest = build_conductor_catalog(ROOT, output)

    assert manifest["catalog_version"] == "v2"
    assert manifest["schema_version"] == "4.2.0"
    assert "generated_at" not in manifest
    assert validate_catalog(output, source_root=ROOT) == []
    assert {file.name: file.read_bytes() for file in v1.iterdir() if file.is_file()} == original
    assert {file.name: file.read_bytes() for file in v1.iterdir() if file.is_file()} != {
        file.name: file.read_bytes() for file in output.iterdir() if file.is_file()
    }
    for name in original.keys() - {"manifest.json", "conductors.parquet"}:
        assert (output / name).read_bytes() == original[name]

    conductors = pd.read_parquet(output / "conductors.parquet")
    provenance = pd.read_parquet(output / "conductor_provenance.parquet")
    issues = pd.read_parquet(output / "conductor_issues.parquet")
    crosswalk = pd.read_parquet(output / "conductor_crosswalk.parquet")
    assert len(conductors) == 641
    assert len(conductors.record_id.unique()) == 641
    assert conductors[conductors.family == "ACSR"].gmr_ft.isna().all()
    raven = conductors[conductors.record_id == "ACSR:1/0:raven:standard:6/1"].iloc[0]
    assert raven.strand_diameter_al_in == "0.1327"
    assert raven.strand_diameter_core_in == "0.1327"
    assert set(provenance[(provenance.record_id == raven.record_id)
                          & (provenance.field == "strand_diameter_core_in")].source_field) == {"strand_diameter_stl_in"}
    assert conductors[conductors.family == "ACCC"].gmr_ft.notna().any()
    assert set(provenance[provenance.field == "gmr_ft"].method) == {"published"}
    tw = conductors[conductors.family == "ACSS/TW"]
    assert len(tw) == 216
    assert tw.dc_resistance_20c_ohm_kft.notna().all()
    assert tw.ampacity_200c_a.notna().all()
    assert len(provenance) > 641
    assert set(provenance.record_id).issubset(set(conductors.record_id))
    assert set(issues.reason) >= {"tw_area_rounding_difference", "incompatible_tw_area", "missing_strength"}
    assert len(issues[issues.reason == "tw_area_rounding_difference"]) == 31
    assert len(issues[issues.reason == "missing_strength"]) == 8
    assert len(crosswalk) == 161
    assert (crosswalk.status == "mapped").any()
    assert set(crosswalk[crosswalk.family.isin(["AAAC", "ACAR"])].status) == {"excluded_family"}
    assert crosswalk[crosswalk.status != "mapped"].new_record_id.isna().all()
    assert crosswalk[crosswalk.status == "mapped"].new_record_id.isin(conductors.record_id).all()
    assert all(source["sha256"] for source in manifest["sources"])
    assert len(manifest["sources"]) == 9
    bluebird = conductors[(conductors.family == "ACSR") & (conductors.codeword == "Bluebird")].iloc[0]
    assert bluebird.total_area_in2 == "1.8309"
    assert set(provenance[(provenance.record_id == bluebird.record_id)
                          & (provenance.field == "total_area_in2")].method) == {"cross_pdf"}

    repository = CatalogRepository(output)
    assert repository.select_exact("conductors", record_id=bluebird.record_id)["variant"] == "standard"
    with pytest.raises(AmbiguousCatalogMatch):
        repository.select_exact("conductors", family="ACCC", codeword="IRVING")
    assert repository.select_exact("conductors", family="ACCC", codeword="IRVING", variant="uls")

    second = tmp_path / "repeat"
    assert build_conductor_catalog(ROOT, second) == manifest
    assert json.loads((second / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert {file.name: file.read_bytes() for file in second.iterdir()} == {
        file.name: file.read_bytes() for file in output.iterdir()
    }


def test_build_v2_refuses_existing_destination(tmp_path: Path) -> None:
    output = tmp_path / "v2"
    output.mkdir()
    with pytest.raises(FileExistsError):
        build_conductor_catalog(ROOT, output)


def test_build_v2_rejects_changed_source_before_writing(tmp_path: Path) -> None:
    source = ROOT / "data/raw/Tower_geometries_DB.xlsx"
    altered = tmp_path / "data/raw/Tower_geometries_DB.xlsx"
    altered.parent.mkdir(parents=True)
    altered.write_bytes(source.read_bytes() + b"modified")
    output = tmp_path / "v2"

    with pytest.raises(ValueError, match="source checksum"):
        build_conductor_catalog(tmp_path, output)
    assert not output.exists()


def test_validate_v2_detects_source_and_provenance_corruption(tmp_path: Path) -> None:
    output = tmp_path / "v2"
    build_conductor_catalog(ROOT, output)
    manifest_file = output / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    original_sha = manifest["sources"][1]["sha256"]
    manifest["sources"][1]["sha256"] = "0" * 64
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    assert any("source checksum" in error for error in validate_catalog(output, source_root=ROOT))

    manifest["sources"][1]["sha256"] = original_sha
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    provenance_file = output / "conductor_provenance.parquet"
    frame = pd.read_parquet(provenance_file)
    frame.loc[0, "field"] = "not_a_conductor_field"
    frame.to_parquet(provenance_file, index=False)
    assert any("provenance field" in error for error in validate_catalog(output, source_root=ROOT))