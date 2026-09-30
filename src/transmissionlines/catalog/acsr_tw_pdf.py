"""Stage published ACSR/TW equal-area candidates without transferring them to ACSR."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_SECTION = "Area Equal to Standard ACSR Sizes"
_COLUMNS = (
    ("codeword", 45, 135, "Code Word", None),
    ("size", 135, 166, "Size (kcmil)", "kcmil"),
    ("type_no", 166, 198, "Type No.", None),
    ("aluminum_area_in2", 198, 238, "Cross Sectional Area (in2) / Alum.", "in2"),
    ("total_area_in2", 238, 275, "Cross Sectional Area (in2) / Total", "in2"),
    ("steel_wire", 340, 404, "Stranding / No. & Diameter Individual Steel Wire", "count x in"),
)
_CODEWORD = re.compile(r"(.+)/TW\Z", re.IGNORECASE)
_SIZE = re.compile(r"\d+(?:\.\d+)?\Z")


@dataclass(frozen=True, kw_only=True)
class TWAreaSourceRow:
    """Retain one published ACSR/TW area candidate and its source cells."""

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


def _area_rows(page: pymupdf.Page) -> list[dict[str, SourceCell]]:
    words = page.get_text("words")
    footnotes = [word[1] for word in words if word[4] == "+Ampacity"]
    if len(footnotes) != 1:
        raise ValueError("missing ACSR/TW area table footnote")
    body = [word for word in words if 215 <= word[1] < footnotes[0]]
    starts = [word for word in body if 45 <= word[0] < 135 and _CODEWORD.fullmatch(word[4])]
    if len(starts) != 20:
        raise ValueError(f"changed ACSR/TW area row count on PDF page {page.number + 1}")
    rows: list[dict[str, SourceCell]] = []
    for index, first in enumerate(starts):
        stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else footnotes[0]
        row_words = [word for word in body if first[1] - 2 <= word[1] < stop]
        cells = {}
        for field, left, right, header, unit in _COLUMNS:
            values = [word[4] for word in row_words if left <= word[0] < right]
            cells[field] = SourceCell(header, " ".join(values) if values else None, unit)
        rows.append(cells)
    return rows


def extract_acsr_tw_areas(path: str | Path) -> list[TWAreaSourceRow]:
    """Stage ACSR/TW equal-area table rows from PDF pages 2 and 3.

    Parameters
    ----------
    path : str or Path
        Southwire ACSR/TW PDF. No catalog or source files are written.

    Returns
    -------
    list[TWAreaSourceRow]
        Published aluminum and total material area candidates with raw-cell
        provenance. No round-wire area is selected by this function.

    Raises
    ------
    ValueError
        If the published section, column headings, or row layout changes.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    staged: list[TWAreaSourceRow] = []
    keys: set[str] = set()
    with pymupdf.open(source) as document:
        if len(document) < 3:
            raise ValueError("missing ACSR/TW area header on PDF pages 2-3")
        for page_number in (2, 3):
            page = document[page_number - 1]
            header = " ".join(page.get_text().split())
            required = (_SECTION, "Cross Sectional Area (in2)", "Alum. Total", "Size (kcmil)")
            if not all(part in header for part in required):
                raise ValueError(f"missing or changed ACSR/TW area header on page {page_number}")
            area_labels = [word for word in page.get_text("words") if 180 < word[1] < 210]
            if not any(198 <= word[0] < 238 and word[4] == "Alum." for word in area_labels) or not any(
                238 <= word[0] < 275 and word[4] == "Total" for word in area_labels
            ):
                raise ValueError(f"changed ACSR/TW area column headings on page {page_number}")
            for cells in _area_rows(page):
                raw_name = cells["codeword"].raw or ""
                name = _CODEWORD.fullmatch(raw_name)
                size = cells["size"].raw
                type_no = cells["type_no"].raw
                if name is None or not size or not _SIZE.fullmatch(size) or not type_no or not type_no.isdecimal():
                    raise ValueError(f"invalid ACSR/TW area row on page {page_number}: {cells!r}")
                for field in ("aluminum_area_in2", "total_area_in2"):
                    parse_numeric_cell(cells[field].raw)
                canonical_size = format(Decimal(size).normalize(), "f")
                codeword = name.group(1)
                key = f"ACSR/TW:{canonical_size}:{codeword.casefold()}:type-{type_no}"
                if key in keys:
                    raise ValueError(f"duplicate ACSR/TW area row key: {key}")
                keys.add(key)
                staged.append(TWAreaSourceRow(source_file=source, source_sha256=digest,
                                              page=page_number, section=_SECTION, table="ACSR/TW",
                                              row_key=key, codeword=codeword, size=canonical_size,
                                              cells=cells))
    return staged
