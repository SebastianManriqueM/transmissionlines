"""Check staged AAC source rows against the Southwire PDF."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.aac_pdf import extract_aac


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/southwire/AAC.pdf"
SHA256 = "e37d00223b4c1fad5476f8d3e96ec0c08b2f54ae9c06d74c71bd8ff93069abb3"


def test_aac_rows_preserve_source_layout_and_awg_identity() -> None:
    rows = extract_aac(PDF)

    assert len(rows) == 56
    assert Counter(row.page for row in rows) == {2: 37, 3: 19}
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert len({row.row_key for row in rows}) == len(rows)
    poppy = next(row for row in rows if row.codeword == "Poppy")
    assert poppy.size == "1/0"
    assert poppy.cells["size"].raw == "1/0"
    assert poppy.cells["class"].raw == "AA, A"
    assert poppy.cells["aluminum_area_in2"].unit == "in2"
    assert "core_diameter_in" not in poppy.cells
    camellia = next(row for row in rows if row.codeword == "Camellia")
    assert camellia.page == 3
    assert camellia.cells["dc_resistance_20c_ohm_kft"].raw == ".0713"
    assert camellia.numeric("dc_resistance_20c_ohm_kft") == Decimal(".0713")


def test_aac_reviewed_cells_preserve_printed_units_and_pages() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/aac_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_aac(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"]
        assert row.source_file == PDF
        assert row.section == "all-aluminum" and row.table == "AAC"
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]
        assert row.cells["aluminum_area_in2"].unit == "in2"
        assert row.cells["dc_resistance_20c_ohm_kft"].unit == "ohm/1000 ft"
        assert row.cells["ampacity_75c_a"].unit == "A"


def test_aac_missing_strength_stays_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing-strength.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[1].search_for("563")
        assert len(rectangles) == 1
        document[1].add_redact_annot(rectangles[0])
        document[1].apply_redactions()
        document.save(path)

    peachbell = next(row for row in extract_aac(path) if row.codeword == "Peachbell")
    assert peachbell.cells["rated_strength_lb"].raw is None
    assert peachbell.numeric("rated_strength_lb") is None


def test_aac_changed_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing-header.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[1].search_for("Ampacity+")
        assert len(rectangles) == 1
        document[1].add_redact_annot(rectangles[0])
        document[1].apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="AAC table header"):
        extract_aac(path)


def test_aac_missing_ampacity_condition_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing-notes.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[2].search_for("+Conductor")
        assert len(rectangles) == 1
        document[2].add_redact_annot(rectangles[0])
        document[2].apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="AAC ampacity condition"):
        extract_aac(path)