"""Stage Southwire ACSR/AW round-wire tables without publishing catalog data."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_COLUMNS = (
    ("codeword", "Code Word", None),
    ("size", "Size (AWG or kcmil)", "AWG or kcmil"),
    ("stranding", "Stranding (Al/Aw)", "wires"),
    ("strand_diameter_al_in", "Diameter (ins.) / Individual Wires / Al", "in"),
    ("strand_diameter_aw_in", "Diameter (ins.) / Individual Wires / Aw", "in"),
    ("core_diameter_in", "Diameter (ins.) / Aw Core", "in"),
    ("diameter_in", "Diameter (ins.) / Comp. Cable", "in"),
    ("weight_al_lb_kft", "Weight Per 1000 ft.(lbs) / Al", "lb/1000 ft"),
    ("weight_aw_lb_kft", "Weight Per 1000 ft.(lbs) / Aw", "lb/1000 ft"),
    ("weight_total_lb_kft", "Weight Per 1000 ft.(lbs) / Total", "lb/1000 ft"),
    ("rated_strength_lb", "Rated Strength (lbs.)", "lb"),
    ("dc_resistance_20c_ohm_kft", "Resistance OHMS/1000 ft. / DC @ 20°C", "ohm/1000 ft"),
    ("ac_resistance_75c_ohm_kft", "Resistance OHMS/1000 ft. / AC @ 75°C", "ohm/1000 ft"),
    ("ampacity_75c_a", "Allowable Ampacity+ (Amps) / 75°C conductor", "A"),
)
_STANDARD_CENTERS = (65, 137, 174, 209, 245, 281, 317, 356, 392, 428, 460, 495, 531, 570)
_HIGH_CENTERS = (39, 90, 131, 168, 207, 247, 288, 327, 366, 406, 445, 485, 525, 568)
_SIZE = re.compile(r"(?:\d+(?:\.\d+)?|[1-4]/0)\Z")
_STRANDING = re.compile(r"\d+/\d+\Z")
_HEADER = (
    "Size (AWG or kcmil)", "(Al/Aw)", "Weight Per 1000 ft.(lbs)",
    "Resistance OHMS/1000 ft.", "DC @ 20°C", "AC @ 75°C",
    "Allowable Ampacity+ (Amps)",
)


@dataclass(frozen=True, kw_only=True)
class ACSRAWSourceRow:
    """Retain an ACSR/AW row, its variant, and its original source cells."""

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
        """Parse a numeric source cell while retaining its printed spelling."""
        return parse_numeric_cell(self.cells[field].raw)


def _columns_at(page: pymupdf.Page, *, first_y: float, last_y: float,
                centers: tuple[int, ...]) -> list[list[str | None]]:
    words = [word for word in page.get_text("words") if first_y <= word[1] < last_y]

    def column(word: tuple[float, float, float, float, str, int, int, int]) -> int:
        return min(range(len(centers)), key=lambda index: abs(word[0] - centers[index]))

    sizes = [word for word in words if column(word) == 1 and _SIZE.fullmatch(word[4])]
    rows: list[list[str | None]] = []
    for index, size in enumerate(sizes):
        start = size[1] - 2
        stop = sizes[index + 1][1] - 2 if index + 1 < len(sizes) else last_y
        columns: list[list[str]] = [[] for _ in centers]
        for word in words:
            if start <= word[1] < stop:
                columns[column(word)].append(word[4])
        rows.append([" ".join(items) if items else None for items in columns])
    return rows


def extract_acsr_aw(path: str | Path) -> list[ACSRAWSourceRow]:
    """Extract standard and high-strength ACSR/AW from PDF pages 2 and 3.

    Parameters
    ----------
    path : str or Path
        Southwire ACSR/AW PDF. No files are written.

    Returns
    -------
    list[ACSRAWSourceRow]
        Staged rows with variant, page, source checksum, and raw-cell provenance.

    Raises
    ------
    ValueError
        If a table header, section boundary, row layout, or row key is invalid.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with pymupdf.open(source) as document:
        if len(document) != 3 or any(
            not all(part in " ".join(document[index].get_text().split()) for part in _HEADER)
            for index in (1, 2)
        ) or "HIGH MECHANICAL STRENGTH" not in document[2].get_text():
            raise ValueError("missing or changed ACSR/AW table header")
        footnotes = [word[1] for word in document[2].get_text("words") if word[4] == "+Conductor"]
        if len(footnotes) != 2:
            raise ValueError("missing ACSR/AW ampacity footnotes")
        sections = (
            (2, 100.0, 750.0, _STANDARD_CENTERS, "standard", "round-wire"),
            (3, 40.0, footnotes[0], _STANDARD_CENTERS, "standard", "round-wire"),
            (3, 420.0, footnotes[1], _HIGH_CENTERS, "high", "high mechanical strength"),
        )
        staged: list[ACSRAWSourceRow] = []
        keys: set[str] = set()
        for page_number, start, stop, centers, variant, section in sections:
            for values in _columns_at(document[page_number - 1], first_y=start,
                                      last_y=stop, centers=centers):
                cells = {
                    field: SourceCell(header, raw, unit)
                    for (field, header, unit), raw in zip(_COLUMNS, values, strict=True)
                }
                raw_name, size, stranding = values[:3]
                name = re.fullmatch(r"(.+)/Aw", raw_name or "", flags=re.IGNORECASE)
                if name is None or not size or not stranding or not _STRANDING.fullmatch(stranding):
                    raise ValueError(f"invalid ACSR/AW row layout on page {page_number}: {values!r}")
                for field in list(cells)[3:]:
                    parse_numeric_cell(cells[field].raw)
                canonical_size = size if "/" in size else format(Decimal(size).normalize(), "f")
                codeword = name.group(1)
                key = f"ACSR/AW:{canonical_size}:{codeword.casefold().replace(' ', '-')}:" \
                      f"{variant}:{stranding}"
                if key in keys:
                    raise ValueError(f"duplicate ACSR/AW row key: {key}")
                keys.add(key)
                staged.append(ACSRAWSourceRow(source_file=source, source_sha256=digest,
                                               page=page_number, section=section,
                                               table="ACSR/AW", row_key=key, codeword=codeword,
                                               size=canonical_size, variant=variant, cells=cells))
    return staged
