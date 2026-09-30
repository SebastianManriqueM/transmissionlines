"""Check ACSR/TW equal-area candidates against the source PDF."""

import json
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.acsr_aw_pdf import extract_acsr_aw
from transmissionlines.catalog.acsr_pdf import extract_acsr
from transmissionlines.catalog.acsr_tw_pdf import extract_acsr_tw_areas


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSR_TW.pdf"
SHA256 = "8f5401d9a7fae338bd6562956de7b995edd4dac36c287bf772181aa38f869fcd"


def test_tw_equal_area_rows_are_source_candidates_not_round_properties() -> None:
    rows = extract_acsr_tw_areas(PDF)

    assert len(rows) == 40
    assert Counter(row.page for row in rows) == {2: 20, 3: 20}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert all(row.source_file == PDF for row in rows)
    assert all(row.section == "Area Equal to Standard ACSR Sizes" for row in rows)
    assert len({row.row_key for row in rows}) == len(rows)
    assert all(set(row.cells) == {"codeword", "size", "type_no", "aluminum_area_in2", "total_area_in2", "steel_wire"} for row in rows)


def test_tw_area_headers_units_and_stable_join_identity() -> None:
    partridge = next(row for row in extract_acsr_tw_areas(PDF) if row.codeword == "Partridge")

    assert partridge.page == 2
    assert partridge.size == "266.8"
    assert partridge.row_key == "ACSR/TW:266.8:partridge:type-16"
    assert partridge.cells["codeword"].raw == "Partridge/TW"
    assert partridge.cells["size"].raw == "266.8"
    assert partridge.cells["type_no"].raw == "16"
    assert partridge.cells["aluminum_area_in2"].raw == "0.2094"
    assert partridge.cells["aluminum_area_in2"].header == "Cross Sectional Area (in2) / Alum."
    assert partridge.cells["aluminum_area_in2"].unit == "in2"
    assert partridge.cells["total_area_in2"].raw == "0.2435"
    assert partridge.cells["total_area_in2"].header == "Cross Sectional Area (in2) / Total"
    assert partridge.cells["steel_wire"].raw == "7 x 0.0788"
    assert partridge.numeric("total_area_in2") == Decimal("0.2435")


def test_tw_reviewed_areas_match_each_page_including_bluebird() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/acsr_tw_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_acsr_tw_areas(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"]
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]


def test_tw_join_keys_are_candidates_only_for_round_wire_sources() -> None:
    keys = {(row.codeword.casefold(), row.size) for row in extract_acsr_tw_areas(PDF)}
    acsr = extract_acsr(PDF.with_name("ACSR.pdf"))
    acsr_aw = extract_acsr_aw(PDF.with_name("ACSR_AW.pdf"))

    assert sum((row.codeword.casefold(), row.size) in keys for row in acsr) == 32
    assert sum((row.codeword.casefold(), row.size) in keys for row in acsr_aw) == 22
    assert ("turkey", "6") not in keys
    assert ("grouse", "80") not in keys


def test_tw_bluebird_printed_aluminum_area_disagrees_with_nominal_size() -> None:
    bluebird = next(row for row in extract_acsr_tw_areas(PDF) if row.codeword == "Bluebird")

    assert bluebird.numeric("aluminum_area_in2") == Decimal("1.0934")
    assert bluebird.numeric("total_area_in2") == Decimal("1.8312")
    nominal_aluminum_in2 = float(bluebird.size) * math.pi / 4000
    assert nominal_aluminum_in2 - float(bluebird.numeric("aluminum_area_in2")) > 0.5


def test_tw_missing_total_area_remains_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing-area.pdf"
    with pymupdf.open(PDF) as document:
        page = document[1]
        rectangles = page.search_for("0.2435")
        assert len(rectangles) == 1
        page.add_redact_annot(rectangles[0])
        page.apply_redactions()
        document.save(path)

    partridge = next(row for row in extract_acsr_tw_areas(path) if row.codeword == "Partridge")
    assert partridge.cells["total_area_in2"].raw is None
    assert partridge.numeric("total_area_in2") is None


def test_tw_missing_equal_area_section_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed.pdf"
    with pymupdf.open(PDF) as document:
        page = document[1]
        rectangles = page.search_for("Area Equal to Standard ACSR Sizes")
        assert len(rectangles) == 1
        page.add_redact_annot(rectangles[0])
        page.apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="ACSR/TW area header"):
        extract_acsr_tw_areas(path)
