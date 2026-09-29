"""Stage ACCC customary-unit source rows without generating catalog variants."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pymupdf

from transmissionlines.catalog.acsr_pdf import SourceCell, parse_numeric_cell


_COLUMNS = (
    ("codeword", 70, "ACCC Conductor / Size Designation", None),
    ("available_uls", 140, "Available as ULS", None),
    ("aluminum_size_kcmil", 161, "Size (kcmil)", "kcmil"),
    ("diameter_in", 185, "Diameter (in.)", "in"),
    ("core_diameter_in", 214, "ACCC Core Diameter (in.)", "in"),
    ("weight_total_lb_kft", 241, "Approximate Weight (1) / Total (lb/kft)", "lb/kft"),
    ("weight_al_lb_kft", 268, "Approximate Weight (1) / Aluminum (lb/kft)", "lb/kft"),
    ("weight_core_lb_kft", 300, "Approximate Weight (1) / Core (lb/kft)", "lb/kft"),
    ("strength_standard_klbf", 333, "Cond. Rated Strength / w/ ACCC Core (klbf)", "klbf"),
    ("strength_uls_klbf", 369, "Cond. Rated Strength / w/ ACCC ULS Core (klbf)", "klbf"),
    ("dc_resistance_20c_ohm_mile", 401, "Resistance / DC @ 20°C (ohm/mile)", "ohm/mile"),
    ("ac_resistance_25c_ohm_mile", 433, "Resistance / AC @ 25°C (ohm/mile)", "ohm/mile"),
    ("ac_resistance_200c_ohm_mile", 466, "Resistance / AC @ 200°C (ohm/mile)", "ohm/mile"),
    ("ampacity_75c_a", 501, "Ampacity (2) / 75°C (amps)", "A"),
    ("ampacity_180c_a", 531, "Ampacity (2) / 180°C (amps)", "A"),
    ("ampacity_200c_a", 562, "Ampacity (2) / 200°C (amps)", "A"),
    ("gmr_ft", 590, "Geometric Mean Radius (ft)", "ft"),
    ("inductive_reactance_ohm_mile", 623, "Inductive Reactance @ 60 Hz (ohms/mile)", "ohm/mile"),
    ("capacitive_reactance_mohm_mile", 657, "Capactive Reactance @ 60Hz (Mohm-mile)", "Mohm-mile"),
    ("commonly_replaces", 705, "Commonly Replaces / Size", None),
)
_REQUIRED = ("ACCC® CONDUCTOR: US CUSTOMARY SIZES", "Available as ULS™", "Approximate Weight (1)",
             "Cond. Rated Strength", "DC @ 20°C", "AC @ 25°C", "AC @ 200°C", "75°C 180°C 200°C",
             "Geometric Mean Radius", "Commonly Replaces")
_SIZE = re.compile(r"\d+(?:\.\d+)?\Z")


@dataclass(frozen=True, kw_only=True)
class ACCCSourceRow:
    """Retain one ACCC table row and its standard and optional ULS cells."""

    source_file: Path
    source_sha256: str
    page: int
    section: str
    table: str
    row_key: str
    codeword: str
    size: str
    cells: dict[str, SourceCell]
    uls_weight_note: str
    ampacity_note: str

    def numeric(self, field: str) -> Decimal | None:
        """Parse a numeric source cell without changing its printed text."""
        return parse_numeric_cell(self.cells[field].raw)


def _footnote(words: list[tuple], marker: str) -> str:
    matching = [word for word in words if word[4] == marker and word[1] > 365]
    if len(matching) != 1:
        raise ValueError(f"missing ACCC footnote {marker}")
    start = matching[0][1]
    return " ".join(word[4] for word in sorted(words, key=lambda word: word[0])
                    if abs(word[1] - start) < 2)


def extract_accc(path: str | Path) -> list[ACCCSourceRow]:
    """Stage ACCC customary-unit rows from the first PDF page.

    Parameters
    ----------
    path : str or Path
        ACCC source PDF. No catalog files or derived ULS measurements are written.

    Returns
    -------
    list[ACCCSourceRow]
        Published rows with standard and optional ULS rated strengths, raw units,
        and the weight and ampacity footnotes.

    Raises
    ------
    ValueError
        If table headings, footnotes, row count, or row identities change.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with pymupdf.open(source) as document:
        if len(document) != 1 or not all(part in " ".join(document[0].get_text().split()) for part in _REQUIRED):
            raise ValueError("missing or changed ACCC table header")
        words = document[0].get_text("words")
        weight_note = _footnote(words, "(1)")
        ampacity_note = _footnote(words, "(2)")
        if "slightly lower weight" not in weight_note or "IEEE 738-2006" not in ampacity_note:
            raise ValueError("missing ACCC weight or ampacity footnote")
        body = [word for word in words if 82 <= word[1] < 365]
        starts = [word for word in body if 157 <= word[0] < 166 and _SIZE.fullmatch(word[4])]
        if len(starts) != 28:
            raise ValueError("changed ACCC row count on PDF page 1")
        centers = [column[1] for column in _COLUMNS]
        staged: list[ACCCSourceRow] = []
        keys: set[str] = set()
        for index, first in enumerate(starts):
            stop = starts[index + 1][1] - 2 if index + 1 < len(starts) else 365
            columns: list[list[str]] = [[] for _ in centers]
            for word in body:
                if first[1] - 2 <= word[1] < stop:
                    nearest = min(range(len(centers)), key=lambda position: abs(word[0] - centers[position]))
                    columns[nearest].append(word[4])
            cells = {
                field: SourceCell(header, " ".join(values) if values else None, unit)
                for (field, _, header, unit), values in zip(_COLUMNS, columns, strict=True)
            }
            codeword = cells["codeword"].raw
            size = cells["aluminum_size_kcmil"].raw
            available = cells["available_uls"].raw
            uls_strength = cells["strength_uls_klbf"].raw
            if not codeword or not size or not _SIZE.fullmatch(size) or available not in ("--", "\uf0fc"):
                raise ValueError(f"invalid ACCC row on PDF page 1: {cells!r}")
            for field in cells.keys() - {"codeword", "available_uls", "commonly_replaces"}:
                parse_numeric_cell(cells[field].raw)
            if (available == "--") != (parse_numeric_cell(uls_strength) is None):
                raise ValueError(f"inconsistent ACCC ULS availability: {cells!r}")
            canonical_size = format(Decimal(size).normalize(), "f")
            key = f"ACCC:{canonical_size}:{codeword.casefold().replace(' ', '-')}"
            if key in keys:
                raise ValueError(f"duplicate ACCC row key: {key}")
            keys.add(key)
            staged.append(ACCCSourceRow(source_file=source, source_sha256=digest,
                                        page=1, section="US customary sizes", table="ACCC",
                                        row_key=key, codeword=codeword, size=canonical_size,
                                        cells=cells, uls_weight_note=weight_note,
                                        ampacity_note=ampacity_note))
    return staged