"""Check source-backed ACCC customary-unit table extraction."""

import json
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.accc_pdf import extract_accc


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/ACCC_electrical_data_ctc.pdf"
SHA256 = "8f31bcbc7c3fc513b6998fba159045157894831a20b5e5ebf13d0556dad482d3"


def test_accc_rows_keep_optional_uls_strength_and_source_units() -> None:
    rows = extract_accc(PDF)

    assert len(rows) == 28
    assert sum(row.numeric("strength_uls_klbf") is not None for row in rows) == 20
    assert {row.source_sha256 for row in rows} == {SHA256}
    assert len({row.row_key for row in rows}) == 28
    oceanside = next(row for row in rows if row.codeword == "OCEANSIDE")
    assert oceanside.cells["strength_uls_klbf"].raw == "--"
    assert oceanside.numeric("strength_uls_klbf") is None
    assert oceanside.cells["weight_total_lb_kft"].raw == "395.2"
    irving = next(row for row in rows if row.codeword == "IRVING")
    assert irving.cells["strength_standard_klbf"].raw == "33.2"
    assert irving.cells["strength_uls_klbf"].raw == "39.0"
    assert irving.numeric("strength_uls_klbf") == Decimal("39.0")
    assert irving.cells["ac_resistance_200c_ohm_mile"].unit == "ohm/mile"
    assert irving.cells["ampacity_180c_a"].unit == "A"


def test_accc_reviewed_cells_and_footnotes_match_source() -> None:
    review = json.loads((Path(__file__).parent / "fixtures/accc_review.json").read_text(encoding="utf-8"))
    rows = {row.row_key: row for row in extract_accc(PDF)}

    assert review["source_sha256"] == SHA256
    for expected in review["rows"]:
        row = rows[expected["row_key"]]
        assert row.page == expected["page"] == 1
        assert row.source_file == PDF
        assert row.table == "ACCC" and row.section == "US customary sizes"
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]
        assert row.cells["strength_standard_klbf"].unit == "klbf"
        assert row.cells["weight_total_lb_kft"].unit == "lb/kft"
        assert "slightly lower weight" in row.uls_weight_note
        assert "IEEE 738-2006" in row.ampacity_note


def test_accc_missing_uls_strength_is_not_a_variant_candidate() -> None:
    rows = extract_accc(PDF)

    assert sum(row.numeric("strength_uls_klbf") is None for row in rows) == 8
    assert all(row.cells["available_uls"].raw == "--" for row in rows
               if row.numeric("strength_uls_klbf") is None)
    assert all(row.cells["available_uls"].raw != "--" for row in rows
               if row.numeric("strength_uls_klbf") is not None)
    assert rows[0].numeric("ampacity_180c_a") == Decimal("938")
    assert next(row for row in rows if row.codeword == "IRVING").numeric("ampacity_180c_a") == Decimal("1280")


def test_accc_changed_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed-header.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[0].search_for("CUSTOMARY")
        assert len(rectangles) == 1
        document[0].add_redact_annot(rectangles[0])
        document[0].apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="ACCC table header"):
        extract_accc(path)


def test_accc_missing_weight_footnote_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "changed-footnote.pdf"
    with pymupdf.open(PDF) as document:
        rectangles = document[0].search_for("slightly lower weight")
        assert len(rectangles) == 1
        document[0].add_redact_annot(rectangles[0])
        document[0].apply_redactions()
        document.save(path)

    with pytest.raises(ValueError, match="ACCC weight or ampacity footnote"):
        extract_accc(path)