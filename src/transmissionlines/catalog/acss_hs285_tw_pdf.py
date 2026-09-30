"""Stage ACSS HS285 shaped-wire source rows without importing round-wire tables."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_SECTION = "Area Equal to ACSS"
_CODEWORD = re.compile(r"(.+)/ACSS/TW\Z", re.IGNORECASE)
_SIZE = re.compile(r"\d+(?:\.\d+)?\Z")
_COLUMNS = (
    ("codeword", 47, "Code Word", None),
    ("size", 102, "Conductor Size (kcmil)", "kcmil"),
    ("type_no", 136, "Type No.", None),
    ("aluminum_area_in2", 165, "Cross Sectional Area Sq In / Alum.", "in2"),
    ("total_area_in2", 197, "Cross Sectional Area Sq In / Total", "in2"),
    ("aluminum_layers", 235, "Stranding / Layers of Alum.", "count"),
    ("aluminum_wires", 266, "Stranding / No.of Alum. Wires", "count"),
    ("steel_wire", 291, "Stranding / No. & Dia. Indv. Steel Wire", "count x in"),
    ("core_diameter_in", 327, "Diameter / Steel Core in", "in"),
    ("diameter_in", 360, "Diameter / Complete Conductor in", "in"),
    ("weight_al_lb_kft", 393, "Weight per 1000 feet / Alum. lb", "lb/1000 ft"),
    ("weight_steel_lb_kft", 425, "Weight per 1000 feet / Steel lb", "lb/1000 ft"),
    ("weight_total_lb_kft", 457, "Weight per 1000 feet / Total lb", "lb/1000 ft"),
    ("strength_standard_lb", 489, "Rated Breaking Strength / Standard Strength lb", "lb"),
    ("strength_high_lb", 521, "Rated Breaking Strength / High Strength lb", "lb"),
    ("strength_hs285_lb", 553, "Rated Breaking Strength / HS285 Strength lb", "lb"),
)
_DIAMETER_COLUMNS = (
    ("codeword", 44, "Code Word", None),
    ("size", 99, "Conductor Size (kcmil)", "kcmil"),
    ("type_no", 126, "Type No.", None),
    ("acsr_size", 143, "Size & Stranding of ACSR with Equal Diameter / kcmil", "kcmil"),
    ("acsr_stranding", 171, "Size & Stranding of ACSR with Equal Diameter / Stranding", "wires"),
    ("aluminum_area_in2", 197, "Cross Sectional Area Sq In / Alum.", "in2"),
    ("total_area_in2", 226, "Cross Sectional Area Sq In / Total", "in2"),
    ("aluminum_layers", 257, "Stranding / Layers of Alum.", "count"),
    ("aluminum_wires", 282, "Stranding / No. & Alum. Wires", "count"),
    ("steel_wire", 303, "Stranding / No. & Dia. Indv. Steel Wire", "count x in"),
    ("core_diameter_in", 336, "Diameter / Steel Core in", "in"),
    ("diameter_in", 367, "Diameter / Complete Conductor in", "in"),
    ("weight_al_lb_kft", 399, "Weight per 1000 feet / Alum. lb", "lb/1000 ft"),
    ("weight_steel_lb_kft", 434, "Weight per 1000 feet / Steel lb", "lb/1000 ft"),
    ("weight_total_lb_kft", 469, "Weight per 1000 feet / Total lb", "lb/1000 ft"),
    ("strength_standard_lb", 500, "Rated Breaking Strength / Standard Strength lb", "lb"),
    ("strength_high_lb", 528, "Rated Breaking Strength / High Strength lb", "lb"),
    ("strength_hs285_lb", 556, "Rated Breaking Strength / HS285 Strength lb", "lb"),
)
_ELECTRICAL_COLUMNS = (
    ("codeword", 46, "Code Word", None),
    ("size", 102, "Conductor Size (kcmil)", "kcmil"),
    ("type_no", 140, "Type No.", None),
    ("dc_resistance_20c_ohm_mile", 171, "Resistance / dc @ 20°C", "ohm/mile"),
    ("ac_resistance_25c_ohm_mile", 205, "Resistance / ac–60 Hz @ 25°C", "ohm/mile"),
    ("ac_resistance_50c_ohm_mile", 240, "Resistance / ac–60 Hz @ 50°C", "ohm/mile"),
    ("ac_resistance_75c_ohm_mile", 275, "Resistance / ac–60 Hz @ 75°C", "ohm/mile"),
    ("gmr_ft", 309, "GMR feet", "ft"),
    ("inductive_xa", 345, "Inductive Xa", "Mohm-mile"),
    ("capacitive_xa", 379, "Capacitive Xa", "Mohm-mile"),
    ("ampacity_75c_a", 416, "Ampacity @ 75°C", "A"),
    ("ampacity_100c_a", 451, "Ampacity @ 100°C", "A"),
    ("ampacity_150c_a", 486, "Ampacity @ 150°C", "A"),
    ("ampacity_200c_a", 520, "Ampacity @ 200°C", "A"),
    ("ampacity_250c_a", 554, "Ampacity @ 250°C", "A"),
)
_PAGE_LAYOUTS = {
    4: ("Area Equal to ACSS", "electrical", _ELECTRICAL_COLUMNS, 38),
    5: ("Diameters Equal to ACSR", "geometry", _DIAMETER_COLUMNS, 34),
    6: ("Diameters Equal to ACSR", "electrical", _ELECTRICAL_COLUMNS, 34),
}


@dataclass(frozen=True, kw_only=True)
class HS285TWSourceRow:
    """Retain a published shaped-wire row and its labeled source cells."""

    source_file: Path
    source_sha256: str
    page: int
    section: str
    table: str
    row_key: str
    codeword: str | None
    size: str
    cells: dict[str, SourceCell]

    def numeric(self, field: str) -> Decimal | None:
        """Parse a printed numeric cell while retaining its raw spelling."""
        return parse_numeric_cell(self.cells[field].raw)


def _area_rows(page: pymupdf.Page) -> list[dict[str, SourceCell]]:
    words = page.get_text("words")
    notes = [word[1] for word in words if word[4] == "Notes:"]
    if len(notes) != 1:
        raise ValueError("missing HS285/TW area notes boundary")
    body = [word for word in words if 145 <= word[1] < notes[0]]
    starts = [word for word in body if word[0] < 90 and _CODEWORD.fullmatch(word[4])]
    if len(starts) != 38:
        raise ValueError("changed HS285/TW area row count on PDF page 3")
    centers = [column[1] for column in _COLUMNS]
    rows: list[dict[str, SourceCell]] = []
    for index, first in enumerate(starts):
        stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else notes[0]
        columns: list[list[str]] = [[] for _ in centers]
        for word in body:
            if first[1] - 2 <= word[1] < stop:
                nearest = min(range(len(centers)), key=lambda position: abs(word[0] - centers[position]))
                columns[nearest].append(word[4])
        rows.append({
            field: SourceCell(header, " ".join(values) if values else None, unit)
            for (field, _, header, unit), values in zip(_COLUMNS, columns, strict=True)
        })
    return rows


def _layout_rows(page: pymupdf.Page, *, page_number: int) -> list[dict[str, SourceCell]]:
    _, _, columns, expected = _PAGE_LAYOUTS[page_number]
    words = page.get_text("words")
    notes = [word[1] for word in words if word[4] == "Notes:"]
    if len(notes) != 1:
        raise ValueError(f"missing HS285/TW notes boundary on page {page_number}")
    body = [word for word in words if 140 <= word[1] < notes[0]]
    size_center = columns[1][1]
    starts = [word for word in body if abs(word[0] - size_center) < 6 and _SIZE.fullmatch(word[4])]
    if len(starts) != expected:
        raise ValueError(f"changed HS285/TW row count on PDF page {page_number}")
    centers = [column[1] for column in columns]
    rows: list[dict[str, SourceCell]] = []
    for index, first in enumerate(starts):
        stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else notes[0]
        values: list[list[str]] = [[] for _ in columns]
        for word in body:
            if first[1] - 2 <= word[1] < stop:
                nearest = min(range(len(centers)), key=lambda position: abs(word[0] - centers[position]))
                values[nearest].append(word[4])
        rows.append({
            field: SourceCell(header, " ".join(items) if items else None, unit)
            for (field, _, header, unit), items in zip(columns, values, strict=True)
        })
    return rows


def extract_acss_hs285_tw(path: str | Path) -> list[HS285TWSourceRow]:
    """Stage HS285 shaped-wire tables on PDF pages 3 through 6.

    Parameters
    ----------
    path : str or Path
        Southwire ACSS HS285 PDF. No catalog files are written.

    Returns
    -------
    list[HS285TWSourceRow]
        Page-specific source rows, including the unnamed equal-diameter row.
        Round-wire tables and cross-PDF area transfers are excluded.

    Raises
    ------
    ValueError
        If a section header, source cell, or row identity changes.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    staged: list[HS285TWSourceRow] = []
    keys: set[str] = set()
    with pymupdf.open(source) as document:
        if len(document) < 6:
            raise ValueError("missing HS285/TW tables")
        for page_number in (3, 4, 5, 6):
            page = document[page_number - 1]
            section, layout, _, _ = _PAGE_LAYOUTS.get(page_number, (_SECTION, "geometry", _COLUMNS, 38))
            header = " ".join(page.get_text().split())
            required = (section, "(ACSS/TW)", "Cross Sectional Area Sq In", "HS285 Strength lb") if page_number == 3 else (
                ("Diameters Equal to ACSR" if page_number in (5, 6) else "Area Equal to ACSS"),
                "(ACSS/TW)", "Resistance" if layout == "electrical" else "Cross Sectional Area Sq In",
            )
            if not all(part in header for part in required):
                raise ValueError(f"missing or changed HS285/TW header on page {page_number}")
            source_rows = _area_rows(page) if page_number == 3 else _layout_rows(page, page_number=page_number)
            for row_index, cells in enumerate(source_rows):
                raw_name = cells["codeword"].raw
                name = _CODEWORD.fullmatch(raw_name or "")
                size = cells["size"].raw
                type_no = cells["type_no"].raw
                anonymous = page_number in (5, 6) and row_index == 0 and raw_name is None
                if (name is None and not anonymous) or not size or not _SIZE.fullmatch(size) or not type_no or not type_no.isdecimal():
                    raise ValueError(f"invalid HS285/TW row on page {page_number}: {cells!r}")
                for field in cells.keys() - {"codeword", "size", "type_no", "steel_wire", "acsr_stranding"}:
                    parse_numeric_cell(cells[field].raw)
                codeword = name.group(1) if name else None
                canonical_size = format(Decimal(size).normalize(), "f")
                label = codeword.casefold() if codeword else "unnamed"
                prefix = "area-equal" if page_number in (3, 4) else "diameter-equal"
                suffix = "" if page_number == 3 else f":{layout}"
                key = f"ACSS/HS285/TW:{prefix}:{canonical_size}:{label}:type-{type_no}{suffix}"
                if key in keys:
                    raise ValueError(f"duplicate HS285/TW row key: {key}")
                keys.add(key)
                staged.append(HS285TWSourceRow(source_file=source, source_sha256=digest,
                                              page=page_number, section=section, table="ACSS/TW",
                                              row_key=key, codeword=codeword, size=canonical_size,
                                              cells=cells))
    return staged
