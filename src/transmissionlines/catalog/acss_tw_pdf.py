"""Stage published ACSS/TW equal-area candidates without assigning round-wire area."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_SECTION = "Area Equal to Standard ACSR Sizes"
_CODEWORD = re.compile(r"(.+)/ACSS/TW\Z", re.IGNORECASE)
_SIZE = re.compile(r"\d+(?:\.\d+)?\Z")
_COLUMNS = {
    2: (
        ("codeword", 40, 127, "Code Word", None),
        ("size", 127, 160, "Size (kcmil)", "kcmil"),
        ("type_no", 160, 181, "Type No.", None),
        ("aluminum_area_in2", 181, 212, "Cross Sectional Area (in2) / Aluminum", "in2"),
        ("total_area_in2", 212, 245, "Cross Sectional Area (in2) / Total", "in2"),
        ("steel_wire", 294, 338, "Stranding / No. & Diameter Individual Steel Wire", "count x in"),
    ),
    3: (
        ("codeword", 40, 134, "Code Word", None),
        ("size", 134, 168, "Size (kcmil)", "kcmil"),
        ("type_no", 168, 188, "Type No.", None),
        ("aluminum_area_in2", 188, 219, "Cross Sectional Area (in2) / Aluminum", "in2"),
        ("total_area_in2", 219, 252, "Cross Sectional Area (in2) / Total", "in2"),
        ("steel_wire", 298, 340, "Stranding / No. & Diameter Individual Steel Wire", "count x in"),
    ),
}


@dataclass(frozen=True, kw_only=True)
class ACSSTWAreaSourceRow:
    """Retain one published ACSS/TW area candidate and its source cells."""

    source_file: Path
    source_sha256: str
    page: int
    section: str
    table: str
    row_key: str
    codeword: str
    size: str
    cells: dict[str, SourceCell]

    def numeric(self, field: str) -> Decimal | None:
        """Parse a numeric source cell without changing its printed value."""
        return parse_numeric_cell(self.cells[field].raw)


def _area_rows(page: pymupdf.Page, page_number: int) -> list[dict[str, SourceCell]]:
    words = page.get_text("words")
    footers = [word[1] for word in words if word[4] == "One" and word[1] > 540]
    if len(footers) != 1:
        raise ValueError(f"missing ACSS/TW table footer on page {page_number}")
    starts = [word for word in words if 40 <= word[0] < 134 and
              190 <= word[1] < footers[0] and _CODEWORD.fullmatch(word[4])]
    expected = {2: 23, 3: 16}[page_number]
    if len(starts) != expected:
        raise ValueError(f"changed ACSS/TW area row count on PDF page {page_number}")
    notes = [word[1] for word in words if word[1] > starts[-1][1] and re.fullmatch(r"\d+\)", word[4])]
    end = min(notes) if notes else footers[0]
    rows: list[dict[str, SourceCell]] = []
    for index, first in enumerate(starts):
        stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else end
        row_words = [word for word in words if first[1] - 2 <= word[1] < stop]
        cells = {}
        for field, left, right, header, unit in _COLUMNS[page_number]:
            values = [word[4] for word in row_words if left <= word[0] < right]
            cells[field] = SourceCell(header, " ".join(values) if values else None, unit)
        rows.append(cells)
    return rows


def extract_acss_tw_areas(path: str | Path) -> list[ACSSTWAreaSourceRow]:
    """Stage ACSS/TW equal-area rows from PDF pages 2 and 3.

    Parameters
    ----------
    path : str or Path
        Southwire ACSS/TW PDF. No catalog or source files are written.

    Returns
    -------
    list[ACSSTWAreaSourceRow]
        Published area candidates with raw-cell provenance, not selected
        round-wire properties.

    Raises
    ------
    ValueError
        If the section, headings, or published row layout changes.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    staged: list[ACSSTWAreaSourceRow] = []
    keys: set[str] = set()
    with pymupdf.open(source) as document:
        if len(document) < 3:
            raise ValueError("missing ACSS/TW area header on PDF pages 2-3")
        for page_number in (2, 3):
            page = document[page_number - 1]
            header = " ".join(page.get_text().split())
            required = (_SECTION, "Cross Sectional Area (in2)", "Size (kcmil)")
            if not all(part in header for part in required):
                raise ValueError(f"missing or changed ACSS/TW area header on page {page_number}")
            labels = [word for word in page.get_text("words") if word[1] < 195]
            aluminum_left = _COLUMNS[page_number][3][1]
            total_left = _COLUMNS[page_number][4][1]
            if not any(aluminum_left <= word[0] < total_left and word[4] == "Aluminum" for word in labels) or not any(
                total_left <= word[0] < _COLUMNS[page_number][4][2] and word[4] == "Total" for word in labels
            ):
                raise ValueError(f"changed ACSS/TW area column headings on page {page_number}")
            for cells in _area_rows(page, page_number):
                raw_name = cells["codeword"].raw or ""
                name = _CODEWORD.fullmatch(raw_name)
                size = cells["size"].raw
                type_no = cells["type_no"].raw
                if name is None or not size or not _SIZE.fullmatch(size) or not type_no or not type_no.isdecimal():
                    raise ValueError(f"invalid ACSS/TW area row on page {page_number}: {cells!r}")
                for field in ("aluminum_area_in2", "total_area_in2"):
                    parse_numeric_cell(cells[field].raw)
                canonical_size = format(Decimal(size).normalize(), "f")
                codeword = name.group(1)
                key = f"ACSS/TW:{canonical_size}:{codeword.casefold()}:type-{type_no}"
                if key in keys:
                    raise ValueError(f"duplicate ACSS/TW area row key: {key}")
                keys.add(key)
                staged.append(ACSSTWAreaSourceRow(source_file=source, source_sha256=digest,
                                                  page=page_number, section=_SECTION, table="ACSS/TW",
                                                  row_key=key, codeword=codeword, size=canonical_size,
                                                  cells=cells))
    return staged
