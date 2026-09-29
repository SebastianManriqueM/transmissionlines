"""Check HS285 shaped-wire source tables without importing round-wire rows."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.acss_hs285_tw_pdf import extract_acss_hs285_tw


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSS Hs285.pdf"
SHA256 = "14dbe01443dd5f3051bc4314527765d8b7ac12e31315e7c9a295201e569a8b9b"


def test_hs285_area_equal_tw_rows_preserve_grade_and_page_provenance() -> None:
    rows = [row for row in extract_acss_hs285_tw(PDF) if row.page == 3]

    assert len(rows) == 38
    assert Counter(row.section for row in rows) == {"Area Equal to ACSS": 38}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert all(row.page == 3 and row.table == "ACSS/TW" for row in rows)
    assert len({row.row_key for row in rows}) == len(rows)
    linnet = next(row for row in rows if row.codeword == "Linnet")
    assert linnet.row_key == "ACSS/HS285/TW:area-equal:336.4:linnet:type-16"
    assert linnet.cells["codeword"].raw == "Linnet/ACSS/TW"
    assert linnet.cells["aluminum_area_in2"].raw == "0.2641"
    assert linnet.cells["total_area_in2"].raw == "0.3070"
    assert linnet.cells["strength_standard_lb"].raw == "11,200"
    assert linnet.cells["strength_high_lb"].raw == "12,300"
    assert linnet.cells["strength_hs285_lb"].raw == "14,400"
    assert linnet.numeric("strength_hs285_lb") == Decimal("14400")


def test_hs285_tw_electrical_rows_keep_their_own_page_and_units() -> None:
    rows = extract_acss_hs285_tw(PDF)

    assert Counter(row.page for row in rows) == {3: 38, 4: 38, 5: 34, 6: 34}
    linnet = next(row for row in rows if row.page == 4 and row.codeword == "Linnet")
    assert linnet.section == "Area Equal to ACSS"
    assert linnet.cells["dc_resistance_20c_ohm_mile"].raw == "0.2588"
    assert linnet.cells["dc_resistance_20c_ohm_mile"].unit == "ohm/mile"
    assert linnet.cells["ampacity_200c_a"].raw == "921"
    assert "strength_hs285_lb" not in linnet.cells


def test_hs285_equal_diameter_keeps_anonymous_first_row_unassigned() -> None:
    rows = extract_acss_hs285_tw(PDF)
    unnamed = [row for row in rows if row.page in (5, 6) and row.codeword is None]

    assert len(unnamed) == 2
    assert {row.section for row in unnamed} == {"Diameters Equal to ACSR"}
    geometry = next(row for row in unnamed if row.page == 5)
    electrical = next(row for row in unnamed if row.page == 6)
    assert geometry.cells["codeword"].raw is None
    assert geometry.cells["size"].raw == "403.4"
    assert geometry.cells["acsr_size"].raw == "336.4"
    assert geometry.cells["acsr_stranding"].raw == "26/7"
    assert geometry.cells["strength_hs285_lb"].raw == "16,700"
    assert electrical.cells["dc_resistance_20c_ohm_mile"].raw == "0.2158"
    assert geometry.row_key != electrical.row_key
    assert all(row.table == "ACSS/TW" and row.source_file == PDF for row in rows)
    assert all(row.cells["codeword"].raw is None or row.cells["codeword"].raw.endswith("/ACSS/TW") for row in rows)


def test_hs285_reviewed_tw_cells_match_the_pdf_on_all_four_pages() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/acss_hs285_tw_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_acss_hs285_tw(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"]
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]
    assert len(rows) == 144
    for first_page, second_page in ((3, 4), (5, 6)):
        first = {(row.codeword, row.size, row.cells["type_no"].raw)
                 for row in rows.values() if row.page == first_page}
        second = {(row.codeword, row.size, row.cells["type_no"].raw)
                  for row in rows.values() if row.page == second_page}
        assert first == second


def test_hs285_missing_area_stays_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[2].search_for("0.3070")
        assert len(rectangles) == 1
        document[2].add_redact_annot(rectangles[0])
        document[2].apply_redactions()
        document.save(path)

    linnet = next(row for row in extract_acss_hs285_tw(path) if row.page == 3 and row.codeword == "Linnet")
    assert linnet.cells["total_area_in2"].raw is None
    assert linnet.numeric("total_area_in2") is None


def test_hs285_missing_equal_diameter_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[4].search_for("Diameters Equal to ACSR")
        assert len(rectangles) == 1
        document[4].add_redact_annot(rectangles[0])
        document[4].apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="HS285/TW header on page 5"):
        extract_acss_hs285_tw(path)
