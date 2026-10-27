"""Check staged PDF table rows against reviewed cells from the pinned sources."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from transmissionlines.catalog.pdf_tables import extract, parse_numeric_cell


RAW = Path(__file__).resolve().parents[2] / "data/raw/conductors"
FIXTURES = Path(__file__).parent / "fixtures"
SOURCES = {  # fixture: (pdf, rows per page)
    "acsr": (RAW / "southwire/ACSR.pdf", {2: 36, 3: 32}),
    "acsr_aw": (RAW / "southwire/ACSR_AW.pdf", {2: 36, 3: 25}),
    "aac": (RAW / "southwire/AAC.pdf", {2: 37, 3: 19}),
    "acss": (RAW / "southwire/ACSS.pdf", {2: 35, 3: 29}),
    "accc": (RAW / "ACCC_electrical_data_ctc.pdf", {1: 28}),
    "acsr_tw": (RAW / "southwire/ACSR_TW.pdf", {2: 20, 3: 20}),
    "acss_tw": (RAW / "southwire/ACSS TW.pdf", {2: 23, 3: 16}),
    "acss_hs285_tw": (RAW / "southwire/ACSS Hs285.pdf", {3: 38, 4: 38, 5: 34, 6: 34}),
}


@pytest.mark.parametrize("name", SOURCES)
def test_rows_match_reviewed_cells(name: str) -> None:
    pdf, pages = SOURCES[name]
    review = json.loads((FIXTURES / f"{name}_review.json").read_text(encoding="utf-8"))
    rows = extract(pdf)
    by_key = {row.row_key: row for row in rows}

    assert Counter(row.page for row in rows) == pages
    assert {row.source_sha256 for row in rows} == {review["source_sha256"]}
    for expected in review["rows"]:
        row = by_key[expected["row_key"]]
        assert row.page == expected["page"]
        assert row.variant == expected.get("variant", row.variant)
        assert {field: row.cells[field].raw for field in expected["raw"]} == expected["raw"]


def test_row_identity_and_units() -> None:
    acsr = {row.codeword: row for row in extract(SOURCES["acsr"][0])}
    assert acsr["Wood Duck"].row_key == "ACSR:605:wood-duck:standard:30/7"
    assert acsr["Wood Duck"].cells["size"].raw == "605.0"
    assert acsr["Raven"].size == "1/0"
    assert acsr["Turkey"].cells["dc_resistance_20c_ohm_kft"].unit == "ohm/1000 ft"
    grouse = next(row for row in extract(SOURCES["acsr_aw"][0]) if row.codeword == "Grouse")
    assert (grouse.variant, grouse.section) == ("high", "high mechanical strength")
    assert grouse.numeric("rated_strength_lb") == Decimal("4890")
    hs285 = extract(SOURCES["acss_hs285_tw"][0])
    assert {row.row_key for row in hs285 if row.codeword is None} == {
        "ACSS/HS285/TW:diameter-equal:403.4:unnamed:type-16:geometry",
        "ACSS/HS285/TW:diameter-equal:403.4:unnamed:type-16:electrical",
    }
    assert any(row.row_key == "ACSS/HS285/TW:diameter-equal:1758.6:pee dee:type-7:geometry" for row in hs285)


def test_redacted_cell_stays_missing_without_shifting_columns(tmp_path: Path) -> None:
    path = tmp_path / "ACSS.pdf"
    with pymupdf.open(SOURCES["acss"][0]) as document:
        (rectangle,) = document[1].search_for("9730")
        document[1].add_redact_annot(rectangle)
        document[1].apply_redactions()
        document.save(path)
    partridge = next(row for row in extract(path) if row.codeword == "Partridge")
    assert partridge.numeric("strength_high_lb") is None
    assert partridge.numeric("strength_standard_lb") == Decimal("8880")
    assert partridge.numeric("strength_hs285_lb") == Decimal("11400")


@pytest.mark.parametrize(("raw", "value"), [
    (None, None), ("", None), ("  ", None), ("-", None), ("--", None), ("1,190", Decimal("1190")),
])
def test_parse_numeric_cell(raw: str | None, value: Decimal | None) -> None:
    assert parse_numeric_cell(raw) == value


def test_parse_numeric_cell_rejects_text() -> None:
    with pytest.raises(ValueError, match="numeric cell"):
        parse_numeric_cell("not measured")
