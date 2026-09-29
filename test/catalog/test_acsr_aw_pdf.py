"""Check staged ACSR/AW extraction against both Southwire table sections."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.acsr_aw_pdf import extract_acsr_aw


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/ACSR_AW.pdf"
SHA256 = "16c764ef84bca4c8411d0272ede1d819ef5ff570a99f7bd471f6d99ae2bfa2bd"


def test_acsr_aw_source_sections_pages_and_unique_keys() -> None:
    rows = extract_acsr_aw(PDF)

    assert len(rows) == 61
    assert Counter(row.variant for row in rows) == {"standard": 52, "high": 9}
    assert Counter(row.page for row in rows) == {2: 36, 3: 25}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert all(row.source_file == PDF and row.table == "ACSR/AW" for row in rows)
    assert len({row.row_key for row in rows}) == len(rows)


def test_acsr_aw_standard_header_units_and_awg_size() -> None:
    rows = extract_acsr_aw(PDF)
    swan = next(row for row in rows if row.codeword == "Swan")
    raven = next(row for row in rows if row.codeword == "Raven")

    assert swan.section == "round-wire"
    assert swan.page == 2
    assert swan.cells["codeword"].raw == "Swan/Aw"
    assert swan.cells["stranding"].header == "Stranding (Al/Aw)"
    assert swan.cells["core_diameter_in"].header == "Diameter (ins.) / Aw Core"
    assert swan.cells["strand_diameter_aw_in"].raw == ".0834"
    assert swan.cells["strand_diameter_aw_in"].unit == "in"
    assert swan.cells["weight_aw_lb_kft"].raw == "16"
    assert swan.cells["weight_aw_lb_kft"].unit == "lb/1000 ft"
    assert swan.cells["rated_strength_lb"].raw == "1780"
    assert swan.cells["dc_resistance_20c_ohm_kft"].raw == ".3917"
    assert swan.cells["dc_resistance_20c_ohm_kft"].unit == "ohm/1000 ft"
    assert swan.cells["ac_resistance_75c_ohm_kft"].raw == ".4770"
    assert swan.cells["ampacity_75c_a"].raw == "145"
    assert raven.size == raven.cells["size"].raw == "1/0"
    assert raven.codeword == "Raven" and raven.row_key.startswith("ACSR/AW:1/0:raven:")


def test_acsr_aw_high_strength_uses_own_header_and_preserves_raw_cells() -> None:
    rows = extract_acsr_aw(PDF)
    grouse = next(row for row in rows if row.codeword == "Grouse")
    cochin = next(row for row in rows if row.codeword == "Cochin")

    assert grouse.page == cochin.page == 3
    assert grouse.variant == cochin.variant == "high"
    assert grouse.section == "high mechanical strength"
    assert grouse.cells["codeword"].raw == "Grouse/AW"
    assert grouse.cells["size"].raw == "80.0" and grouse.size == "80"
    assert grouse.cells["rated_strength_lb"].raw == "4,890"
    assert grouse.numeric("rated_strength_lb") == Decimal("4890")
    assert grouse.cells["weight_total_lb_kft"].raw == "137.7"
    assert cochin.cells["rated_strength_lb"].raw == "19,800"
    assert cochin.numeric("rated_strength_lb") == Decimal("19800")


def test_acsr_aw_reviewed_cells_match_both_pages_and_sections() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/acsr_aw_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_acsr_aw(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert (row.page, row.variant) == (expected["page"], expected["variant"])
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]


def test_acsr_aw_absent_measurement_remains_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing-strength.pdf"
    with pymupdf.open(PDF) as document:
        page = document[2]
        rectangles = page.search_for("4,890")
        assert len(rectangles) == 1
        page.add_redact_annot(rectangles[0])
        page.apply_redactions()
        document.save(path)

    grouse = next(row for row in extract_acsr_aw(path) if row.codeword == "Grouse")
    assert grouse.cells["rated_strength_lb"].raw is None
    assert grouse.numeric("rated_strength_lb") is None


def test_acsr_aw_missing_high_strength_label_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing-high-label.pdf"
    with pymupdf.open(PDF) as document:
        page = document[2]
        rectangles = page.search_for("HIGH MECHANICAL STRENGTH")
        assert len(rectangles) == 1
        page.add_redact_annot(rectangles[0])
        page.apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="ACSR/AW table header"):
        extract_acsr_aw(path)



def test_acsr_aw_missing_high_section_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed.pdf"
    document = pymupdf.open()
    document.new_page()
    document.new_page()
    document.new_page()
    document.save(path)
    document.close()

    with pytest.raises(ValueError, match="ACSR/AW table header"):
        extract_acsr_aw(path)