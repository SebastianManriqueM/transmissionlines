"""Stage round-wire ACSR rows from the Southwire PDF without publishing a catalog."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymupdf


_COLUMNS = (
    ("codeword", "Code Word", None),
    ("size", "Size (AWG or kcmil)", "AWG or kcmil"),
    ("stranding", "Stranding (Al/Stl)", "wires"),
    ("strand_diameter_al_in", "Diameter (ins.) / Individual Wires / Al", "in"),
    ("strand_diameter_stl_in", "Diameter (ins.) / Individual Wires / Stl", "in"),
    ("core_diameter_in", "Diameter (ins.) / Steel Core", "in"),
    ("diameter_in", "Diameter (ins.) / Complete Cable", "in"),
    ("weight_al_lb_kft", "Weight Per 1000 ft. (lbs.) / Al", "lb/1000 ft"),
    ("weight_stl_lb_kft", "Weight Per 1000 ft. (lbs.) / Stl", "lb/1000 ft"),
    ("weight_total_lb_kft", "Weight Per 1000 ft. (lbs.) / Total", "lb/1000 ft"),
    ("content_al_percent", "Content (%) / Al", "%"),
    ("content_stl_percent", "Content (%) / Stl", "%"),
    ("rated_strength_lb", "Rated Strength (lbs.)", "lb"),
    ("dc_resistance_20c_ohm_kft", "Resistance OHMS/1000 ft. / DC @ 20°C", "ohm/1000 ft"),
    ("ac_resistance_75c_ohm_kft", "Resistance OHMS/1000 ft. / AC @ 75°C", "ohm/1000 ft"),
    ("ampacity_75c_a", "Allowable Ampacity+ (Amps) / 75°C conductor", "A"),
)
_CENTERS = (53, 88, 123, 158, 193, 228, 263, 298, 333, 368, 403, 438, 473, 508, 543, 576)
_SIZE = re.compile(r"(?:\d+(?:\.\d+)?|[1-4]/0)\Z")
_MISSING = {"", "-", "--", "–", "—"}


@dataclass(frozen=True)
class SourceCell:
    """Retain one source cell's printed header, value, and unit."""

    header: str
    raw: str | None
    unit: str | None


@dataclass(frozen=True)
class ACSRSourceRow:
    """Retain an ACSR table row before normalization into catalog records."""

    source_file: Path
    source_sha256: str
    page: int
    section: str
    table: str
    row_key: str
    codeword: str
    size: str
    variant: str
    cells: dict[str, SourceCell]

    def numeric(self, field: str) -> Decimal | None:
        """Parse a staged numeric cell while preserving its raw spelling."""
        return parse_numeric_cell(self.cells[field].raw)


def parse_numeric_cell(raw: str | None) -> Decimal | None:
    """Parse a printed numeric cell, leaving blank and dash cells absent.

    Parameters
    ----------
    raw : str or None
        Source cell text, possibly containing a thousands separator.

    Returns
    -------
    Decimal or None
        Printed numeric value, or None for a missing cell.

    Raises
    ------
    ValueError
        If the cell contains other text.
    """
    if raw is None or raw.strip() in _MISSING:
        return None
    try:
        return Decimal(raw.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric cell: {raw!r}") from exc


def _column(x: float) -> int:
    return min(range(len(_CENTERS)), key=lambda index: abs(x - _CENTERS[index]))


def _table_rows(page: pymupdf.Page, *, first_y: float) -> list[list[str | None]]:
    page_words = page.get_text("words")
    footnotes = [word[1] for word in page_words if word[4] == "+Conductor"]
    last_y = min(footnotes) if footnotes else 750
    words = [word for word in page_words if first_y <= word[1] < last_y]
    sizes = [word for word in words if _column(word[0]) == 1 and _SIZE.fullmatch(word[4])]
    rows: list[list[str | None]] = []
    for index, size in enumerate(sizes):
        start = size[1] - 2
        stop = sizes[index + 1][1] - 2 if index + 1 < len(sizes) else last_y
        columns: list[list[str]] = [[] for _ in _COLUMNS]
        for word in words:
            if start <= word[1] < stop:
                columns[_column(word[0])].append(word[4])
        rows.append([" ".join(column) if column else None for column in columns])
    return rows


def extract_acsr(path: str | Path) -> list[ACSRSourceRow]:
    """Extract checked ACSR round-wire tables from PDF pages 2 and 3.

    Parameters
    ----------
    path : str or Path
        Southwire ACSR source PDF. No files are written.

    Returns
    -------
    list[ACSRSourceRow]
        Staged rows with PDF page, source hash, and raw-cell provenance.

    Raises
    ------
    ValueError
        If the expected table header, footer, or row layout has changed.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with pymupdf.open(source) as document:
        if len(document) < 3:
            raise ValueError("missing ACSR table header on PDF page 2")
        header = " ".join(document[1].get_text().split())
        required = (
            "Size (AWG or kcmil)", "(Al/Stl)", "Weight Per 1000 ft. (lbs.)",
            "Resistance OHMS/1000 ft.", "DC @ 20°C", "AC @ 75°C",
            "Allowable Ampacity+ (Amps)",
        )
        if not all(part in header for part in required):
            raise ValueError("missing or changed ACSR table header on PDF page 2")
        if "Conductor temperature of 75°C" not in document[2].get_text():
            raise ValueError("missing ACSR ampacity condition on PDF page 3")
        staged: list[ACSRSourceRow] = []
        keys: set[str] = set()
        for page_number, first_y in ((2, 100), (3, 40)):
            for values in _table_rows(document[page_number - 1], first_y=first_y):
                cells = {
                    field: SourceCell(header, raw, unit)
                    for (field, header, unit), raw in zip(_COLUMNS, values, strict=True)
                }
                codeword, size, stranding = values[:3]
                if not codeword or not size or not stranding or not re.fullmatch(r"\d+/\d+", stranding):
                    raise ValueError(f"invalid ACSR row layout on PDF page {page_number}: {values!r}")
                for field in list(cells)[3:]:
                    parse_numeric_cell(cells[field].raw)
                canonical_size = size if "/" in size else format(Decimal(size), "f").rstrip("0").rstrip(".") if "." in size else size
                key = f"ACSR:{canonical_size}:{codeword.casefold().replace(' ', '-')}:standard:{stranding}"
                if key in keys:
                    raise ValueError(f"duplicate ACSR row key: {key}")
                keys.add(key)
                staged.append(ACSRSourceRow(source, digest, page_number, "round-wire", "ACSR", key,
                                            codeword, canonical_size, "standard", cells))
    return staged