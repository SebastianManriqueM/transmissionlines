"""Check ACSS/TW equal-area candidates against the source PDF."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.acss_tw_pdf import extract_acss_tw_areas
from transmissionlines.catalog.acsr_tw_pdf import extract_acsr_tw_areas


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSS TW.pdf"
SHA256 = "590cf5d520a113cba11fe9b0d480cdc444d9b528cde8cf0e51f15cdf43b6258b"


def test_acss_tw_rows_and_page_specific_area_cells() -> None:
    rows = extract_acss_tw_areas(PDF)

    assert len(rows) == 39
    assert Counter(row.page for row in rows) == {2: 23, 3: 16}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert len({row.row_key for row in rows}) == 39
    partridge = next(row for row in rows if row.codeword == "Partridge")
    assert partridge.page == 2
    assert partridge.row_key == "ACSS/TW:266.8:partridge:type-16"
    assert partridge.cells["codeword"].raw == "Partridge/ACSS/TW"
    assert partridge.cells["aluminum_area_in2"].raw == "0.2094"
    assert partridge.cells["total_area_in2"].raw == "0.2435"
    assert partridge.cells["total_area_in2"].unit == "in2"
    assert partridge.numeric("total_area_in2") == Decimal("0.2435")


def test_acss_tw_reviewed_raw_cells_match_both_pdf_pages() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/acss_tw_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_acss_tw_areas(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"]
        assert row.source_file == PDF
        assert row.section == "Area Equal to Standard ACSR Sizes"
        assert row.table == "ACSS/TW"
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]
        assert row.cells["aluminum_area_in2"].header == "Cross Sectional Area (in2) / Aluminum"
        assert row.cells["total_area_in2"].header == "Cross Sectional Area (in2) / Total"


def test_tw_shared_keys_keep_both_printed_total_areas() -> None:
    acss = {(row.codeword.casefold(), row.size): row for row in extract_acss_tw_areas(PDF)}
    acsr = {(row.codeword.casefold(), row.size): row for row in extract_acsr_tw_areas(PDF.with_name("ACSR_TW.pdf"))}
    shared = acss.keys() & acsr.keys()
    half_printed_area_precision_in2 = Decimal("0.00005")
    differences = {
        key: (acss[key].numeric("total_area_in2"), acsr[key].numeric("total_area_in2"))
        for key in shared
        if abs(acss[key].numeric("total_area_in2") - acsr[key].numeric("total_area_in2")) > half_printed_area_precision_in2
    }

    assert len(shared) == 37
    assert acss.keys() - acsr.keys() == {("canary", "900"), ("grackle", "1192.5")}
    assert {key[0] for key in differences} == {
        "scoter", "chukar", "finch", "oriole", "hen", "linnet", "bluebird"
    }
    assert differences[("bluebird", "2156")] == (Decimal("1.8309"), Decimal("1.8312"))
    assert acss[("bluebird", "2156")].numeric("aluminum_area_in2") == Decimal("1.6933")
    assert acsr[("bluebird", "2156")].numeric("aluminum_area_in2") == Decimal("1.0934")


def test_acss_tw_missing_total_area_remains_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing-area.pdf"
    with pymupdf.open(PDF) as document:
        page = document[2]
        rectangles = page.search_for("1.8309")
        assert len(rectangles) == 1
        page.add_redact_annot(rectangles[0])
        page.apply_redactions()
        document.save(path)

    bluebird = next(row for row in extract_acss_tw_areas(path) if row.codeword == "Bluebird")
    assert bluebird.cells["total_area_in2"].raw is None
    assert bluebird.numeric("total_area_in2") is None


def test_acss_tw_missing_section_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed.pdf"
    with pymupdf.open(PDF) as document:
        page = document[1]
        rectangles = page.search_for("Area Equal to Standard ACSR Sizes")
        assert len(rectangles) == 1
        page.add_redact_annot(rectangles[0])
        page.apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="ACSS/TW area header"):
        extract_acss_tw_areas(path)
