"""Check unpublished, source-backed conductor candidates."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from transmissionlines.catalog.acss_pdf import extract_acss
from transmissionlines.catalog.acss_hs285_tw_pdf import extract_acss_hs285_tw
from transmissionlines.catalog.acss_tw_pdf import extract_acss_tw_areas
from transmissionlines.catalog.acsr_pdf import extract_acsr
from transmissionlines.catalog.acsr_aw_pdf import extract_acsr_aw
from transmissionlines.catalog.acsr_tw_pdf import extract_acsr_tw_areas
from transmissionlines.catalog.aac_pdf import extract_aac
from transmissionlines.catalog.accc_pdf import extract_accc
from transmissionlines.catalog.conductor_staging import stage_acss, stage_sources
from transmissionlines.catalog.mechanical_area import resolve_areas


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSS.pdf"


def test_acss_stages_only_printed_strengths_with_stable_ids() -> None:
    rows = extract_acss(PDF)
    staged = stage_acss(rows)

    partridge = {item.variant: item for item in staged if item.source.codeword == "Partridge"}
    assert {grade: item.rated_strength_lb for grade, item in partridge.items()} == {
        "standard": Decimal("8880"), "high": Decimal("9730"), "hs285": Decimal("11400")
    }
    assert partridge["hs285"].record_id == "ACSS:266.8:partridge:26/7:hs285"
    assert partridge["hs285"].strength_cell is partridge["hs285"].source.cells["strength_hs285_lb"]
    assert {item.record_id for item in staged} == {item.record_id for item in stage_acss(reversed(rows))}
    assert len({item.record_id for item in staged}) == len(staged)


def test_acss_rejects_duplicate_identity() -> None:
    row = extract_acss(PDF)[0]

    with pytest.raises(ValueError, match="duplicate conductor ID"):
        stage_acss([row, row])


def test_existing_acsr_construction_keys_remain_candidate_ids() -> None:
    base = PDF.parent
    acsr = extract_acsr(base / "ACSR.pdf")[0]
    acsr_aw = extract_acsr_aw(base / "ACSR_AW.pdf")[0]

    staged = stage_sources(acsr=[acsr], acsr_aw=[acsr_aw])

    assert {item.record_id for item in staged.candidates} == {acsr.row_key, acsr_aw.row_key}


def test_source_staging_keeps_constructions_and_missing_grades_distinct() -> None:
    base = PDF.parent
    result = stage_sources(
        acsr=extract_acsr(base / "ACSR.pdf"),
        acsr_aw=extract_acsr_aw(base / "ACSR_AW.pdf"),
        acss=extract_acss(PDF),
        aac=extract_aac(base / "AAC.pdf"),
        accc=extract_accc(PDF.parents[1] / "ACCC_electrical_data_ctc.pdf"),
        hs285_tw=extract_acss_hs285_tw(base / "ACSS Hs285.pdf"),
    )
    assert len({item.record_id for item in result.candidates}) == len(result.candidates)
    assert {(item.family, item.variant) for item in result.candidates} >= {
        ("ACSR", "standard"), ("ACSR/AW", "high"), ("ACSS", "hs285"),
        ("AAC", "standard"), ("ACCC", "uls"), ("ACSS/TW", "hs285"),
    }
    assert len([item for item in result.candidates if item.family == "ACCC" and item.variant == "uls"]) == 20
    irving = {item.variant: item for item in result.candidates if item.codeword == "IRVING"}
    assert irving["uls"].weight_total_lb_kft == irving["standard"].weight_total_lb_kft == Decimal("648.3")
    assert irving["uls"].weight_basis == "shared_approximation"
    assert irving["uls"].weight_cell is irving["standard"].weight_cell
    assert all(item.source.page in (3, 5) for item in result.candidates if item.family == "ACSS/TW")
    assert any(item.codeword is None and item.source.page == 5 for item in result.candidates)
    assert any(issue.reason == "missing_strength" for issue in result.issues)


def test_round_wire_area_prefers_verified_family_tw_and_derives_without_match() -> None:
    partridge = next(row for row in extract_acss(PDF) if row.codeword == "Partridge")
    source = stage_sources(acss=[partridge])
    tw = extract_acss_tw_areas(PDF.with_name("ACSS TW.pdf"))
    selected = resolve_areas(source, acss_tw=tw)
    from_tw = selected.records[0].area
    assert from_tw is not None
    assert from_tw.total.method == "cross_pdf"
    assert from_tw.total.source_rows[0].source_file == PDF.with_name("ACSS TW.pdf")
    assert from_tw.total.value == from_tw.total.source_rows[0].numeric("total_area_in2")

    derived = resolve_areas(source).records[0].area
    assert derived is not None
    assert derived.total.method == "derived"
    assert derived.total.value == derived.aluminum.value + derived.core.value
    assert {item.field for item in derived.total.input_cells} == {
        "stranding", "strand_diameter_al_in", "strand_diameter_steel_in"
    }


def test_area_missing_geometry_and_incompatible_tw_are_audited() -> None:
    partridge = next(row for row in extract_acss(PDF) if row.codeword == "Partridge")
    tw = next(row for row in extract_acss_tw_areas(PDF.with_name("ACSS TW.pdf"))
              if row.codeword == "Partridge" and row.size == partridge.size)
    cells = dict(tw.cells)
    cells["total_area_in2"] = replace(cells["total_area_in2"], raw="100")
    invalid = resolve_areas(stage_sources(acss=[partridge]), acss_tw=[replace(tw, cells=cells)])
    assert invalid.records[0].area is not None
    assert invalid.records[0].area.total.method == "derived"
    assert any(issue.reason == "incompatible_tw_area" for issue in invalid.issues)

    source_cells = dict(partridge.cells)
    source_cells["strand_diameter_steel_in"] = replace(source_cells["strand_diameter_steel_in"], raw=None)
    missing = resolve_areas(stage_sources(acss=[replace(partridge, cells=source_cells)]))
    assert missing.records[0].area is None
    assert any(issue.reason == "missing_geometry" for issue in missing.issues)


def test_overlapping_and_duplicate_tw_keys_are_not_silently_resolved() -> None:
    partridge = next(row for row in extract_acss(PDF) if row.codeword == "Partridge")
    tw = next(row for row in extract_acss_tw_areas(PDF.with_name("ACSS TW.pdf"))
              if row.codeword == "Partridge" and row.size == partridge.size)
    cells = dict(tw.cells)
    cells["total_area_in2"] = replace(cells["total_area_in2"],
                                       raw=str(tw.numeric("total_area_in2") + Decimal("0.001")))
    conflicting = replace(tw, cells=cells)
    staged = stage_sources(acss=[partridge])

    overlap = resolve_areas(staged, acss_tw=[tw], acsr_tw=[conflicting])
    assert overlap.records[0].area is not None
    assert overlap.records[0].area.total.source_rows == (tw,)
    assert any(issue.reason == "tw_area_disagreement" for issue in overlap.issues)

    duplicated = resolve_areas(staged, acss_tw=[tw, tw])
    assert duplicated.records[0].area is not None
    assert duplicated.records[0].area.total.method == "derived"
    assert any(issue.reason == "ambiguous_tw_area" for issue in duplicated.issues)


def test_accc_uls_area_reuses_assumed_core_and_aac_published_area() -> None:
    accc = next(row for row in extract_accc(PDF.parents[1] / "ACCC_electrical_data_ctc.pdf")
                if row.codeword == "IRVING")
    aac = extract_aac(PDF.with_name("AAC.pdf"))[0]
    result = resolve_areas(stage_sources(accc=[accc], aac=[aac]))
    standard, uls = (next(record.area for record in result.records if record.candidate.family == "ACCC"
                          and record.candidate.variant == variant) for variant in ("standard", "uls"))
    assert standard is not None and uls is not None
    assert uls.total.value == standard.total.value
    assert uls.core.method == "assumed"
    assert uls.core.source_rows == (accc,)
    published = next(record.area for record in result.records if record.candidate.family == "AAC")
    assert published is not None
    assert published.total.method == "published"
    assert published.core is None


def test_full_source_inventory_resolves_or_reports_every_candidate() -> None:
    base = PDF.parent
    staged = stage_sources(
        acsr=extract_acsr(base / "ACSR.pdf"),
        acsr_aw=extract_acsr_aw(base / "ACSR_AW.pdf"),
        acss=extract_acss(PDF), aac=extract_aac(base / "AAC.pdf"),
        accc=extract_accc(PDF.parents[1] / "ACCC_electrical_data_ctc.pdf"),
        hs285_tw=extract_acss_hs285_tw(base / "ACSS Hs285.pdf"),
    )
    result = resolve_areas(staged, acsr_tw=extract_acsr_tw_areas(base / "ACSR_TW.pdf"),
                           acss_tw=extract_acss_tw_areas(base / "ACSS TW.pdf"))
    assert len(result.records) == len(staged.candidates)
    assert all(record.area is not None or any(issue.row_key == record.candidate.source.row_key
                                               for issue in result.issues) for record in result.records)
    assert any(record.area is not None and record.area.total.method == "cross_pdf"
               for record in result.records)
    assert any(record.area is not None and record.area.total.method == "derived"
               for record in result.records)