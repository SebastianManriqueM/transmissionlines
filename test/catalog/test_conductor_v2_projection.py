"""Check unpublished v2 record and field-level source projection."""

from pathlib import Path

from transmissionlines.catalog.accc_pdf import extract_accc
from transmissionlines.catalog.acss_pdf import extract_acss
from transmissionlines.catalog.acss_tw_pdf import extract_acss_tw_areas
from transmissionlines.catalog.conductor_staging import stage_sources
from transmissionlines.catalog.conductor_v2 import project_conductor
from transmissionlines.catalog.mechanical_area import resolve_areas


BASE = Path(__file__).resolve().parents[2] / "data/raw/conductors"


def test_projection_retains_transferred_area_and_published_strength_sources() -> None:
    acss = BASE / "southwire" / "ACSS.pdf"
    partridge = next(row for row in extract_acss(acss) if row.codeword == "Partridge")
    tw = next(row for row in extract_acss_tw_areas(acss.with_name("ACSS TW.pdf"))
              if row.codeword == "Partridge" and row.size == partridge.size)
    staged = resolve_areas(stage_sources(acss=[partridge]), acss_tw=[tw])
    candidate = next(item for item in staged.records if item.candidate.variant == "standard")

    record, provenance = project_conductor(candidate)

    assert record.variant == "standard"
    assert record.source_id == partridge.source_sha256
    assert record.rated_strength_lb == candidate.candidate.rated_strength_lb
    assert record.total_area_in2 == tw.numeric("total_area_in2")
    assert record.core_area_in2 == tw.numeric("total_area_in2") - tw.numeric("aluminum_area_in2")
    assert record.model_validate_json(record.model_dump_json()) == record
    strength = next(item for item in provenance if item.field == "rated_strength_lb")
    assert (strength.source_id, strength.row_key, strength.source_field) == (
        partridge.source_sha256, partridge.row_key, "strength_standard_lb")
    assert strength.raw_value == partridge.cells["strength_standard_lb"].raw
    total = next(item for item in provenance if item.field == "total_area_in2")
    assert total.method == "cross_pdf"
    assert (total.row_key, total.raw_value, total.page) == (
        tw.row_key, tw.cells["total_area_in2"].raw, tw.page)
    assert {item.source_field for item in provenance if item.field == "core_area_in2"} == {
        "aluminum_area_in2", "total_area_in2"}
    for field, source_field in (
        ("size", "size"), ("stranding", "stranding"), ("diameter_inch", "diameter_in"),
    ):
        assert any(item.field == field and item.source_field == source_field
                   and item.row_key == partridge.row_key for item in provenance)


def test_projection_retains_uls_assumptions_and_absent_values() -> None:
    irving = next(row for row in extract_accc(BASE / "ACCC_electrical_data_ctc.pdf")
                  if row.codeword == "IRVING")
    staged = resolve_areas(stage_sources(accc=[irving]))
    candidate = next(item for item in staged.records if item.candidate.variant == "uls")

    record, provenance = project_conductor(candidate)

    assert record.stranding is None
    assert record.weight_lb_kft == candidate.candidate.weight_total_lb_kft
    assert record.total_area_in2 is not None
    assert record.ampacity_temperature_c is None
    weight = next(item for item in provenance if item.field == "weight_lb_kft")
    assert weight.method == "assumed"
    assert weight.raw_value == irving.cells["weight_total_lb_kft"].raw
    assert {item.method for item in provenance if item.field == "total_area_in2"} == {"assumed"}


def test_projection_of_missing_area_keeps_null_and_no_area_provenance() -> None:
    acss = BASE / "southwire" / "ACSS.pdf"
    partridge = next(row for row in extract_acss(acss) if row.codeword == "Partridge")
    candidate = resolve_areas(stage_sources(acss=[partridge])).records[0]
    without_area = type(candidate)(candidate=candidate.candidate, area=None)

    record, provenance = project_conductor(without_area)

    assert record.total_area_in2 is None
    assert not any(item.field.endswith("_area_in2") for item in provenance)