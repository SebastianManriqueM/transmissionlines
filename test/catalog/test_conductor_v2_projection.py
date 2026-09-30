"""Check unpublished v2 record and field-level source projection."""

from decimal import Decimal
from pathlib import Path

from transmissionlines.catalog.accc_pdf import extract_accc
from transmissionlines.catalog.acss_pdf import extract_acss
from transmissionlines.catalog.acss_hs285_tw_pdf import extract_acss_hs285_tw
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
    assert record.ac_resistance_75c_ohm_kft == partridge.numeric("ac_resistance_75c_ohm_kft")
    assert record.ampacity_200c_a == partridge.numeric("ampacity_200c_a")
    assert record.ampacity_temperature_c == 200
    assert any(item.field == "ampacity_200c_a" and item.source_field == "ampacity_200c_a"
               and item.raw_value == partridge.cells["ampacity_200c_a"].raw for item in provenance)


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
    assert record.ac_resistance_25c_ohm_kft == irving.numeric("ac_resistance_25c_ohm_mile") / Decimal("5.28")
    assert record.ac_resistance_200c_ohm_kft == irving.numeric("ac_resistance_200c_ohm_mile") / Decimal("5.28")
    assert record.ampacity_180c_a == irving.numeric("ampacity_180c_a")
    assert any(item.field == "ac_resistance_25c_ohm_kft"
               and item.source_field == "ac_resistance_25c_ohm_mile"
               and item.method == "derived" and item.unit == "ohm/mile" for item in provenance)


def test_projection_of_missing_area_keeps_null_and_no_area_provenance() -> None:
    acss = BASE / "southwire" / "ACSS.pdf"
    partridge = next(row for row in extract_acss(acss) if row.codeword == "Partridge")
    candidate = resolve_areas(stage_sources(acss=[partridge])).records[0]
    without_area = type(candidate)(candidate=candidate.candidate, area=None)

    record, provenance = project_conductor(without_area)

    assert record.total_area_in2 is None
    assert not any(item.field.endswith("_area_in2") for item in provenance)


def test_hs285_tw_electrical_join_keeps_its_own_pdf_page() -> None:
    rows = extract_acss_hs285_tw(BASE / "southwire/ACSS Hs285.pdf")
    geometry = next(row for row in rows if row.page == 3 and row.codeword == "Linnet")
    electrical = next(row for row in rows if row.page == 4 and row.codeword == "Linnet")
    candidate = resolve_areas(stage_sources(hs285_tw=[geometry])).records[0]

    record, provenance = project_conductor(candidate, electrical_row=electrical)

    assert record.dc_resistance_20c_ohm_kft == electrical.numeric("dc_resistance_20c_ohm_mile") / Decimal("5.28")
    assert record.ampacity_200c_a == electrical.numeric("ampacity_200c_a")
    assert any(item.field == "ampacity_200c_a" and item.page == 4
               and item.row_key == electrical.row_key for item in provenance)