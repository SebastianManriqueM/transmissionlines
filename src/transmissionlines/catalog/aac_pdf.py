"""Stage AAC source rows from the Southwire PDF without publishing a catalog."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_COLUMNS = (
    ("codeword", 65, "Code Word", None),
    ("size", 120, "Size (AWG or kcmil)", "AWG or kcmil"),
    ("aluminum_wires", 169, "Stranding / No. of Wires", "count"),
    ("class", 211, "Stranding / Class", None),
    ("strand_diameter_al_in", 252, "Diameter (ins.) / Individual Wires", "in"),
    ("diameter_in", 298, "Diameter (ins.) / Complete Cable", "in"),
    ("aluminum_area_in2", 347, "Cross-Sectional Area (Sq. ins.)", "in2"),
    ("weight_total_lb_kft", 391, "Weight Per 1000 ft. (lbs.)", "lb/1000 ft"),
    ("rated_strength_lb", 434, "Rated Strength (lbs.)", "lb"),
    ("dc_resistance_20c_ohm_kft", 478, "Resistance OHMS/1000 ft. / DC @ 20°C", "ohm/1000 ft"),
    ("ac_resistance_75c_ohm_kft", 524, "Resistance OHMS/1000 ft. / AC @ 75°C", "ohm/1000 ft"),
    ("ampacity_75c_a", 568, "Allowable Ampacity+ (Amps) / 75°C conductor", "A"),
)
_SIZE = re.compile(r"(?:[1-4]/0|\d+(?:\.\d+)?)\Z")
_HEADER = ("(AWG or kcmil)", "No. of Wires", "Class", "Cross- Sectional Area",
           "Rated Strength", "OHMS/1000 ft.", "DC @ 20°C", "AC @ 75°C", "Ampacity+")


@dataclass(frozen=True, kw_only=True)
class AACSourceRow:
    """Retain one published AAC row and its labeled source cells."""

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
        """Parse a printed numeric cell while retaining its raw spelling."""
        return parse_numeric_cell(self.cells[field].raw)


def _rows_on_page(page: pymupdf.Page, *, page_number: int, end: float) -> list[dict[str, SourceCell]]:
    words = [word for word in page.get_text("words") if (95 if page_number == 2 else 40) <= word[1] < end]
    starts = [word for word in words if abs(word[0] - 120) < 10 and _SIZE.fullmatch(word[4])]
    expected = {2: 37, 3: 19}[page_number]
    if len(starts) != expected:
        raise ValueError(f"changed AAC row count on PDF page {page_number}")
    centers = [column[1] for column in _COLUMNS]
    rows: list[dict[str, SourceCell]] = []
    for index, first in enumerate(starts):
        stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else end
        columns: list[list[str]] = [[] for _ in centers]
        for word in words:
            if first[1] - 2 <= word[1] < stop:
                nearest = min(range(len(centers)), key=lambda position: abs(word[0] - centers[position]))
                columns[nearest].append(word[4])
        rows.append({
            field: SourceCell(header, " ".join(values) if values else None, unit)
            for (field, _, header, unit), values in zip(_COLUMNS, columns, strict=True)
        })
    return rows


def extract_aac(path: str | Path) -> list[AACSourceRow]:
    """Stage AAC conductor rows from PDF pages 2 and 3.

    Parameters
    ----------
    path : str or Path
        Southwire AAC PDF. No catalog files are written.

    Returns
    -------
    list[AACSourceRow]
        Printed rows with source cells, including AWG sizes and stranding class.

    Raises
    ------
    ValueError
        If the header, ampacity condition, row layout, or identity changes.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    staged: list[AACSourceRow] = []
    keys: set[str] = set()
    with pymupdf.open(source) as document:
        if len(document) != 3 or not all(part in " ".join(document[1].get_text().split()) for part in _HEADER):
            raise ValueError("missing or changed AAC table header")
        notes = [word[1] for word in document[2].get_text("words") if word[4] == "+Conductor"]
        if len(notes) != 1 or "temperature of 75ºC" not in document[2].get_text():
            raise ValueError("missing AAC ampacity condition")
        for page_number, end in ((2, 700.0), (3, notes[0])):
            for cells in _rows_on_page(document[page_number - 1], page_number=page_number, end=end):
                codeword = cells["codeword"].raw
                size = cells["size"].raw
                wires = cells["aluminum_wires"].raw
                stranding_class = cells["class"].raw
                if (not codeword or not size or not _SIZE.fullmatch(size) or not wires
                        or not wires.isdecimal() or not stranding_class
                        or not re.fullmatch(r"(?:AA|A|B|C)(?:, (?:AA|A|B|C))*", stranding_class)):
                    raise ValueError(f"invalid AAC row on PDF page {page_number}: {cells!r}")
                for field in cells.keys() - {"codeword", "size", "class"}:
                    parse_numeric_cell(cells[field].raw)
                canonical_size = size if "/" in size else format(Decimal(size).normalize(), "f")
                key = f"AAC:{canonical_size}:{codeword.casefold().replace(' ', '-')}:{wires}"
                if key in keys:
                    raise ValueError(f"duplicate AAC row key: {key}")
                keys.add(key)
                staged.append(AACSourceRow(source_file=source, source_sha256=digest,
                                           page=page_number, section="all-aluminum", table="AAC",
                                           row_key=key, codeword=codeword, size=canonical_size,
                                           cells=cells))
    return staged