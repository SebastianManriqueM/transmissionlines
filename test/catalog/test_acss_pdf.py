"""Check round-wire ACSS source rows against the Southwire PDF."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.acss_pdf import extract_acss
from transmissionlines.catalog.acss_tw_pdf import extract_acss_tw_areas


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSS.pdf"
SHA256 = "9babdd90889e32e01ecde6fb7ca628c9456576282001f20d9a559df5e5e3c669"


def test_acss_printed_rows_retain_distinct_strength_columns() -> None:
    rows = extract_acss(PDF)

    assert len(rows) == 64
    assert Counter(row.page for row in rows) == {2: 35, 3: 29}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert len({row.row_key for row in rows}) == len(rows)
    partridge = next(row for row in rows if row.codeword == "Partridge")
    assert partridge.row_key == "ACSS:266.8:partridge:26/7"
    assert partridge.cells["codeword"].raw == "Partridge/ACSS"
    assert partridge.cells["strength_standard_lb"].raw == "8880"
    assert partridge.cells["strength_high_lb"].raw == "9730"
    assert partridge.cells["strength_hs285_lb"].raw == "11400"
    assert partridge.cells["ampacity_200c_a"].raw == "812"
    assert partridge.cells["ampacity_200c_a"].unit == "A"
    assert partridge.numeric("strength_high_lb") == Decimal("9730")


def test_acss_reviewed_cells_retain_source_units_and_page_positions() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/acss_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_acss(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"]
        assert row.source_file == PDF
        assert row.section == "round-wire" and row.table == "ACSS"
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]
        assert row.cells["weight_total_lb_kft"].unit == "lb/1000 ft"
        assert row.cells["dc_resistance_20c_ohm_kft"].unit == "ohm/1000 ft"
        assert row.cells["ac_resistance_75c_ohm_kft"].header.endswith("AC @ 75°C")
        assert row.cells["strength_hs285_lb"].header.endswith("HS285** Strength")


def test_acss_tw_keys_are_candidates_not_source_measurements() -> None:
    rows = extract_acss(PDF)
    keys = {(row.codeword.casefold(), row.size) for row in extract_acss_tw_areas(PDF.with_name("ACSS TW.pdf"))}

    assert sum((row.codeword.casefold(), row.size) in keys for row in rows) == 31
    assert all("total_area_in2" not in row.cells for row in rows)


def test_acss_missing_high_strength_remains_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing-strength.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[1].search_for("9730")
        assert len(rectangles) == 1
        document[1].add_redact_annot(rectangles[0])
        document[1].apply_redactions()
        document.save(path)

    partridge = next(row for row in extract_acss(path) if row.codeword == "Partridge")
    assert partridge.cells["strength_high_lb"].raw is None
    assert partridge.numeric("strength_high_lb") is None
    assert partridge.numeric("strength_standard_lb") == Decimal("8880")


def test_acss_missing_strength_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed-header.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[1].search_for("HS285**")
        assert len(rectangles) == 1
        document[1].add_redact_annot(rectangles[0])
        document[1].apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="ACSS table header"):
        extract_acss(path)
