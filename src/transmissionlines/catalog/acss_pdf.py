"""Stage Southwire ACSS round-wire rows without publishing catalog data."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_COLUMNS = (
    ("codeword", "Code Word", None),
    ("size", "Size (kcmil)", "kcmil"),
    ("stranding", "Stranding (Al/St)", "wires"),
    ("strand_diameter_al_in", "Diameter (in) / Individual Wires / Al", "in"),
    ("strand_diameter_steel_in", "Diameter (in) / Individual Wires / Steel", "in"),
    ("core_diameter_in", "Diameter (in) / Steel Core", "in"),
    ("diameter_in", "Diameter (in) / Comp Cable", "in"),
    ("weight_al_lb_kft", "Weight (lbs/1000 ft) / Al", "lb/1000 ft"),
    ("weight_steel_lb_kft", "Weight (lbs/1000 ft) / Steel", "lb/1000 ft"),
    ("weight_total_lb_kft", "Weight (lbs/1000 ft) / Total", "lb/1000 ft"),
    ("strength_standard_lb", "Rated Strength (lbs) / Standard Strength", "lb"),
    ("strength_high_lb", "Rated Strength (lbs) / High* Strength", "lb"),
    ("strength_hs285_lb", "Rated Strength (lbs) / HS285** Strength", "lb"),
    ("dc_resistance_20c_ohm_kft", "Resistance (OHMS/1000ft) / DC @ 20°C", "ohm/1000 ft"),
    ("ac_resistance_75c_ohm_kft", "Resistance (OHMS/1000ft) / AC @ 75°C", "ohm/1000 ft"),
    ("ampacity_200c_a", "Ampacity @ 200°C (AMPS)", "A"),
)
_CENTERS = {
    2: (30, 100, 134, 161, 193, 224, 258, 287, 314, 344, 380, 421, 459, 497, 528, 567),
    3: (31, 106, 136, 163, 195, 226, 258, 287, 316, 343, 380, 421, 461, 499, 530, 567),
}
_CODEWORD = re.compile(r"(.+)/ACSS\Z", re.IGNORECASE)
_SIZE = re.compile(r"\d+(?:\.\d+)?\Z")
_STRANDING = re.compile(r"\d+/\d+\Z")
_HEADER = ("Size (kcmil)", "(Al/St)", "(OHMS/1000ft)",
           "Standard Strength", "High* Strength", "HS285** Strength", "@ 200°C (AMPS)")


@dataclass(frozen=True, kw_only=True)
class ACSSSourceRow:
    """Retain one printed ACSS row and its separately labeled strength cells."""

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
        """Parse a numeric source cell while retaining its printed spelling."""
        return parse_numeric_cell(self.cells[field].raw)


def _rows_on_page(page: pymupdf.Page, *, page_number: int, end: float) -> list[list[str | None]]:
    words = [word for word in page.get_text("words") if 140 <= word[1] < end]
    starts = [word for word in words if word[0] < 90 and _CODEWORD.fullmatch(word[4])]
    expected = {2: 35, 3: 29}[page_number]
    if len(starts) != expected:
        raise ValueError(f"changed ACSS row count on PDF page {page_number}")
    centers = _CENTERS[page_number]
    rows: list[list[str | None]] = []
    for index, first in enumerate(starts):
        stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else end
        columns: list[list[str]] = [[] for _ in centers]
        for word in words:
            if first[1] - 2 <= word[1] < stop:
                column = min(range(len(centers)), key=lambda position: abs(word[0] - centers[position]))
                columns[column].append(word[4])
        rows.append([" ".join(items) if items else None for items in columns])
    return rows


def extract_acss(path: str | Path) -> list[ACSSSourceRow]:
    """Stage round-wire ACSS source rows from PDF pages 2 and 3.

    Parameters
    ----------
    path : str or Path
        Southwire ACSS PDF. No catalog or source files are written.

    Returns
    -------
    list[ACSSSourceRow]
        Printed rows with raw cells for standard, high, and HS285 strengths.
        Variant records are not selected or generated here.

    Raises
    ------
    ValueError
        If a table header, row layout, or stable row key is invalid.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    staged: list[ACSSSourceRow] = []
    keys: set[str] = set()
    with pymupdf.open(source) as document:
        if len(document) != 3 or any(
            not all(part in " ".join(document[index].get_text().split()) for part in _HEADER)
            for index in (1, 2)
        ):
            raise ValueError("missing or changed ACSS table header")
        notes = [word[1] for word in document[2].get_text("words") if word[4] == "Notes:"]
        if len(notes) != 1:
            raise ValueError("missing ACSS notes boundary")
        for page_number, end in ((2, 700.0), (3, notes[0])):
            for values in _rows_on_page(document[page_number - 1], page_number=page_number, end=end):
                cells = {
                    field: SourceCell(header, raw, unit)
                    for (field, header, unit), raw in zip(_COLUMNS, values, strict=True)
                }
                name = _CODEWORD.fullmatch(values[0] or "")
                size, stranding = values[1:3]
                if name is None or not size or not _SIZE.fullmatch(size) or not stranding or not _STRANDING.fullmatch(stranding):
                    raise ValueError(f"invalid ACSS row on page {page_number}: {values!r}")
                for field in list(cells)[3:]:
                    parse_numeric_cell(cells[field].raw)
                canonical_size = format(Decimal(size).normalize(), "f")
                codeword = name.group(1)
                key = f"ACSS:{canonical_size}:{codeword.casefold().replace(' ', '-')}:{stranding}"
                if key in keys:
                    raise ValueError(f"duplicate ACSS row key: {key}")
                keys.add(key)
                staged.append(ACSSSourceRow(source_file=source, source_sha256=digest,
                                            page=page_number, section="round-wire", table="ACSS",
                                            row_key=key, codeword=codeword, size=canonical_size,
                                            cells=cells))
    return staged
