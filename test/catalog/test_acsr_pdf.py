"""Check staged ACSR extraction against the immutable Southwire PDF."""

import json
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.acsr_pdf import extract_acsr, parse_numeric_cell


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSR.pdf"
SHA256 = "8bb6b7e2f0d1448c70f8337dd6ae65796b7cbfa36d145a454bdfba09afd1bf4f"


def test_acsr_rows_have_checked_source_and_pdf_pages() -> None:
    rows = extract_acsr(PDF)

    assert len(rows) == 68
    assert {row.page for row in rows} == {2, 3}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert all(row.source_file == PDF and row.section == "round-wire" for row in rows)
    assert len({row.row_key for row in rows}) == len(rows)


def test_acsr_reviewed_cells_match_both_pdf_pages() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/acsr_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_acsr(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"]
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]


def test_acsr_header_units_and_published_cells() -> None:
    turkey = next(row for row in extract_acsr(PDF) if row.codeword == "Turkey")

    assert turkey.page == 2
    assert turkey.cells["size"].raw == "6"
    assert turkey.cells["size"].header == "Size (AWG or kcmil)"
    assert turkey.cells["strand_diameter_al_in"].raw == ".0661"
    assert turkey.cells["strand_diameter_al_in"].unit == "in"
    assert turkey.cells["weight_total_lb_kft"].raw == "36"
    assert turkey.cells["weight_total_lb_kft"].unit == "lb/1000 ft"
    assert turkey.cells["rated_strength_lb"].raw == "1190"
    assert turkey.cells["dc_resistance_20c_ohm_kft"].raw == ".641"
    assert turkey.cells["dc_resistance_20c_ohm_kft"].unit == "ohm/1000 ft"
    assert turkey.cells["ac_resistance_75c_ohm_kft"].raw == ".806"
    assert turkey.cells["ampacity_75c_a"].raw == "105"
    assert turkey.cells["ampacity_75c_a"].unit == "A"
    assert turkey.numeric("rated_strength_lb") == Decimal("1190")


def test_acsr_awg_wrapped_name_and_stable_size_identity() -> None:
    rows = extract_acsr(PDF)
    raven = next(row for row in rows if row.codeword == "Raven")
    wood_duck = next(row for row in rows if row.codeword == "Wood Duck")
    squab = next(row for row in rows if row.codeword == "Squab")
    scoter = next(row for row in rows if row.codeword == "Scoter")

    assert raven.size == "1/0"
    assert raven.cells["size"].raw == "1/0"
    assert wood_duck.size == squab.size == "605"
    assert wood_duck.cells["size"].raw == "605.0"
    assert squab.cells["size"].raw == "605"
    assert wood_duck.row_key != squab.row_key
    assert scoter.page == 3
    assert scoter.cells["size"].raw == "636.0"
    assert [row.row_key for row in rows] == [row.row_key for row in extract_acsr(PDF)]


@pytest.mark.parametrize("raw", [None, "", "  ", "-", "--"])
def test_acsr_missing_numeric_cells_stay_missing(raw: str | None) -> None:
    assert parse_numeric_cell(raw) is None


def test_acsr_numeric_cells_accept_commas_but_reject_unexpected_text() -> None:
    assert parse_numeric_cell("1,190") == Decimal("1190")
    with pytest.raises(ValueError, match="numeric cell"):
        parse_numeric_cell("not measured")


def test_acsr_missing_stacked_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed.pdf"
    document = pymupdf.open()
    document.new_page()
    document.new_page()
    document.new_page()
    document.save(path)
    document.close()

    with pytest.raises(ValueError, match="ACSR table header"):
        extract_acsr(path)