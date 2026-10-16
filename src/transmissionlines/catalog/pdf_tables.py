"""Stage conductor table rows from the pinned manufacturer PDFs.

Every table is described by data (`TABLES`): where each region sits on its page,
where its columns are, and what its text cells look like. The sources are pinned
by SHA-256 in `conductor_v2_build`, so coordinates are fixed numbers. The exact
row count per region is the check that the coordinates still fit.
"""

import hashlib
import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class SourceCell:
    """One printed cell: its column header, raw text, and unit."""

    header: str
    raw: str | None
    unit: str | None


@dataclass(frozen=True, kw_only=True)
class SourceRow:
    """One printed table row with raw-cell provenance."""

    source_file: Path
    source_sha256: str
    page: int
    section: str
    table: str
    row_key: str
    codeword: str | None
    size: str
    cells: dict[str, SourceCell]
    variant: str | None = None

    def numeric(self, field: str) -> Decimal | None:
        """Parse a numeric cell, keeping blank and dash cells absent."""
        return parse_numeric_cell(self.cells[field].raw)


def parse_numeric_cell(raw: str | None) -> Decimal | None:
    """Parse printed numeric text such as ``"4,890"``; blank or dash cells are None."""
    if raw is None or raw.strip() in {"", "-", "--", "–", "—"}:
        return None
    try:
        return Decimal(raw.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric cell: {raw!r}") from exc


@dataclass(frozen=True)
class Region:
    """One table block on one page.

    ``x`` holds either column centers (a word goes to the nearest one) or
    ``(left, right)`` bounds (words outside every column are dropped). A row
    starts at each word in the ``anchor`` column matching that field's pattern.
    """

    page: int
    top: float
    bottom: float
    rows: int
    fields: tuple[tuple[str, str, str | None], ...]
    x: tuple
    section: str
    key: str
    anchor: str = "size"
    variant: str | None = None
    unnamed_first_row: bool = False


@dataclass(frozen=True)
class Table:
    """A PDF's tables: text-cell patterns plus regions. Other cells must be numeric."""

    name: str
    patterns: dict[str, str]
    regions: tuple[Region, ...]
    free_text: frozenset[str] = frozenset()
    size_field: str = "size"


_AWG_SIZE = r"\d+(?:\.\d+)?|[1-4]/0"
_SIZE = r"\d+(?:\.\d+)?"
_STRANDING = r"\d+/\d+"

_ACSR = (
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
_ACSR_X = (53, 88, 123, 158, 193, 228, 263, 298, 333, 368, 403, 438, 473, 508, 543, 576)
_ACSR_KEY = "ACSR:{size}:{slug}:{variant}:{stranding}"

_ACSR_AW = (
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
_ACSR_AW_X = (65, 137, 174, 209, 245, 281, 317, 356, 392, 428, 460, 495, 531, 570)
_ACSR_AW_HIGH_X = (39, 90, 131, 168, 207, 247, 288, 327, 366, 406, 445, 485, 525, 568)
_ACSR_AW_KEY = "ACSR/AW:{size}:{slug}:{variant}:{stranding}"

_AAC = (
    ("codeword", "Code Word", None),
    ("size", "Size (AWG or kcmil)", "AWG or kcmil"),
    ("aluminum_wires", "Stranding / No. of Wires", "count"),
    ("class", "Stranding / Class", None),
    ("strand_diameter_al_in", "Diameter (ins.) / Individual Wires", "in"),
    ("diameter_in", "Diameter (ins.) / Complete Cable", "in"),
    ("aluminum_area_in2", "Cross-Sectional Area (Sq. ins.)", "in2"),
    ("weight_total_lb_kft", "Weight Per 1000 ft. (lbs.)", "lb/1000 ft"),
    ("rated_strength_lb", "Rated Strength (lbs.)", "lb"),
    ("dc_resistance_20c_ohm_kft", "Resistance OHMS/1000 ft. / DC @ 20°C", "ohm/1000 ft"),
    ("ac_resistance_75c_ohm_kft", "Resistance OHMS/1000 ft. / AC @ 75°C", "ohm/1000 ft"),
    ("ampacity_75c_a", "Allowable Ampacity+ (Amps) / 75°C conductor", "A"),
)
_AAC_X = (65, 120, 169, 211, 252, 298, 347, 391, 434, 478, 524, 568)
_AAC_KEY = "AAC:{size}:{slug}:{aluminum_wires}"

_ACSS = (
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
_ACSS_KEY = "ACSS:{size}:{slug}:{stranding}"

_ACCC = (
    ("codeword", "ACCC Conductor / Size Designation", None),
    ("available_uls", "Available as ULS", None),
    ("aluminum_size_kcmil", "Size (kcmil)", "kcmil"),
    ("diameter_in", "Diameter (in.)", "in"),
    ("core_diameter_in", "ACCC Core Diameter (in.)", "in"),
    ("weight_total_lb_kft", "Approximate Weight (1) / Total (lb/kft)", "lb/kft"),
    ("weight_al_lb_kft", "Approximate Weight (1) / Aluminum (lb/kft)", "lb/kft"),
    ("weight_core_lb_kft", "Approximate Weight (1) / Core (lb/kft)", "lb/kft"),
    ("strength_standard_klbf", "Cond. Rated Strength / w/ ACCC Core (klbf)", "klbf"),
    ("strength_uls_klbf", "Cond. Rated Strength / w/ ACCC ULS Core (klbf)", "klbf"),
    ("dc_resistance_20c_ohm_mile", "Resistance / DC @ 20°C (ohm/mile)", "ohm/mile"),
    ("ac_resistance_25c_ohm_mile", "Resistance / AC @ 25°C (ohm/mile)", "ohm/mile"),
    ("ac_resistance_200c_ohm_mile", "Resistance / AC @ 200°C (ohm/mile)", "ohm/mile"),
    ("ampacity_75c_a", "Ampacity (2) / 75°C (amps)", "A"),
    ("ampacity_180c_a", "Ampacity (2) / 180°C (amps)", "A"),
    ("ampacity_200c_a", "Ampacity (2) / 200°C (amps)", "A"),
    ("gmr_ft", "Geometric Mean Radius (ft)", "ft"),
    ("inductive_reactance_ohm_mile", "Inductive Reactance @ 60 Hz (ohms/mile)", "ohm/mile"),
    ("capacitive_reactance_mohm_mile", "Capactive Reactance @ 60Hz (Mohm-mile)", "Mohm-mile"),
    ("commonly_replaces", "Commonly Replaces / Size", None),
)
_ACCC_X = (70, 140, 161, 185, 214, 241, 268, 300, 333, 369, 401, 433, 466, 501, 531, 562, 590, 623, 657, 705)

_TW_SECTION = "Area Equal to Standard ACSR Sizes"


def _tw_area(aluminum: str) -> tuple[tuple[str, str, str | None], ...]:
    return (
        ("codeword", "Code Word", None),
        ("size", "Size (kcmil)", "kcmil"),
        ("type_no", "Type No.", None),
        ("aluminum_area_in2", f"Cross Sectional Area (in2) / {aluminum}", "in2"),
        ("total_area_in2", "Cross Sectional Area (in2) / Total", "in2"),
        ("steel_wire", "Stranding / No. & Diameter Individual Steel Wire", "count x in"),
    )


_HS285_AREA = (
    ("codeword", "Code Word", None),
    ("size", "Conductor Size (kcmil)", "kcmil"),
    ("type_no", "Type No.", None),
    ("aluminum_area_in2", "Cross Sectional Area Sq In / Alum.", "in2"),
    ("total_area_in2", "Cross Sectional Area Sq In / Total", "in2"),
    ("aluminum_layers", "Stranding / Layers of Alum.", "count"),
    ("aluminum_wires", "Stranding / No.of Alum. Wires", "count"),
    ("steel_wire", "Stranding / No. & Dia. Indv. Steel Wire", "count x in"),
    ("core_diameter_in", "Diameter / Steel Core in", "in"),
    ("diameter_in", "Diameter / Complete Conductor in", "in"),
    ("weight_al_lb_kft", "Weight per 1000 feet / Alum. lb", "lb/1000 ft"),
    ("weight_steel_lb_kft", "Weight per 1000 feet / Steel lb", "lb/1000 ft"),
    ("weight_total_lb_kft", "Weight per 1000 feet / Total lb", "lb/1000 ft"),
    ("strength_standard_lb", "Rated Breaking Strength / Standard Strength lb", "lb"),
    ("strength_high_lb", "Rated Breaking Strength / High Strength lb", "lb"),
    ("strength_hs285_lb", "Rated Breaking Strength / HS285 Strength lb", "lb"),
)
_HS285_DIAMETER = (
    ("codeword", "Code Word", None),
    ("size", "Conductor Size (kcmil)", "kcmil"),
    ("type_no", "Type No.", None),
    ("acsr_size", "Size & Stranding of ACSR with Equal Diameter / kcmil", "kcmil"),
    ("acsr_stranding", "Size & Stranding of ACSR with Equal Diameter / Stranding", "wires"),
    ("aluminum_area_in2", "Cross Sectional Area Sq In / Alum.", "in2"),
    ("total_area_in2", "Cross Sectional Area Sq In / Total", "in2"),
    ("aluminum_layers", "Stranding / Layers of Alum.", "count"),
    ("aluminum_wires", "Stranding / No. & Alum. Wires", "count"),
    ("steel_wire", "Stranding / No. & Dia. Indv. Steel Wire", "count x in"),
    ("core_diameter_in", "Diameter / Steel Core in", "in"),
    ("diameter_in", "Diameter / Complete Conductor in", "in"),
    ("weight_al_lb_kft", "Weight per 1000 feet / Alum. lb", "lb/1000 ft"),
    ("weight_steel_lb_kft", "Weight per 1000 feet / Steel lb", "lb/1000 ft"),
    ("weight_total_lb_kft", "Weight per 1000 feet / Total lb", "lb/1000 ft"),
    ("strength_standard_lb", "Rated Breaking Strength / Standard Strength lb", "lb"),
    ("strength_high_lb", "Rated Breaking Strength / High Strength lb", "lb"),
    ("strength_hs285_lb", "Rated Breaking Strength / HS285 Strength lb", "lb"),
)
_HS285_ELECTRICAL = (
    ("codeword", "Code Word", None),
    ("size", "Conductor Size (kcmil)", "kcmil"),
    ("type_no", "Type No.", None),
    ("dc_resistance_20c_ohm_mile", "Resistance / dc @ 20°C", "ohm/mile"),
    ("ac_resistance_25c_ohm_mile", "Resistance / ac–60 Hz @ 25°C", "ohm/mile"),
    ("ac_resistance_50c_ohm_mile", "Resistance / ac–60 Hz @ 50°C", "ohm/mile"),
    ("ac_resistance_75c_ohm_mile", "Resistance / ac–60 Hz @ 75°C", "ohm/mile"),
    ("gmr_ft", "GMR feet", "ft"),
    ("inductive_xa", "Inductive Xa", "Mohm-mile"),
    ("capacitive_xa", "Capacitive Xa", "Mohm-mile"),
    ("ampacity_75c_a", "Ampacity @ 75°C", "A"),
    ("ampacity_100c_a", "Ampacity @ 100°C", "A"),
    ("ampacity_150c_a", "Ampacity @ 150°C", "A"),
    ("ampacity_200c_a", "Ampacity @ 200°C", "A"),
    ("ampacity_250c_a", "Ampacity @ 250°C", "A"),
)
_HS285_ELECTRICAL_X = (46, 102, 140, 171, 205, 240, 275, 309, 345, 379, 416, 451, 486, 520, 554)
_HS285_KEY = "ACSS/HS285/TW:{prefix}:{size}:{name}:type-{type_no}"

TABLES = {
    "ACSR.pdf": Table("ACSR", {"codeword": "(.+)", "size": _AWG_SIZE, "stranding": _STRANDING}, (
        Region(2, 100, 750, 36, _ACSR, _ACSR_X, "round-wire", _ACSR_KEY, variant="standard"),
        Region(3, 40, 558.7, 32, _ACSR, _ACSR_X, "round-wire", _ACSR_KEY, variant="standard"),
    )),
    "ACSR_AW.pdf": Table("ACSR/AW", {"codeword": "(?i)(.+)/Aw", "size": _AWG_SIZE, "stranding": _STRANDING}, (
        Region(2, 100, 750, 36, _ACSR_AW, _ACSR_AW_X, "round-wire", _ACSR_AW_KEY, variant="standard"),
        Region(3, 40, 303.2, 16, _ACSR_AW, _ACSR_AW_X, "round-wire", _ACSR_AW_KEY, variant="standard"),
        Region(3, 420, 568.0, 9, _ACSR_AW, _ACSR_AW_HIGH_X, "high mechanical strength", _ACSR_AW_KEY,
               variant="high"),
    )),
    "AAC.pdf": Table("AAC", {"codeword": "(.+)", "size": _AWG_SIZE, "aluminum_wires": r"\d+",
                             "class": r"(?:AA|A|B|C)(?:, (?:AA|A|B|C))*"}, (
        Region(2, 95, 700, 37, _AAC, _AAC_X, "all-aluminum", _AAC_KEY),
        Region(3, 40, 350.6, 19, _AAC, _AAC_X, "all-aluminum", _AAC_KEY),
    )),
    "ACSS.pdf": Table("ACSS", {"codeword": "(?i)(.+)/ACSS", "size": _SIZE, "stranding": _STRANDING}, (
        Region(2, 140, 700, 35, _ACSS,
               (30, 100, 134, 161, 193, 224, 258, 287, 314, 344, 380, 421, 459, 497, 528, 567),
               "round-wire", _ACSS_KEY, anchor="codeword"),
        Region(3, 140, 582.0, 29, _ACSS,
               (31, 106, 136, 163, 195, 226, 258, 287, 316, 343, 380, 421, 461, 499, 530, 567),
               "round-wire", _ACSS_KEY, anchor="codeword"),
    )),
    "ACCC_electrical_data_ctc.pdf": Table(
        "ACCC", {"codeword": "(.+)", "aluminum_size_kcmil": _SIZE, "available_uls": "--|"},
        (Region(1, 82, 365, 28, _ACCC, _ACCC_X, "US customary sizes", "ACCC:{size}:{slug}",
                anchor="aluminum_size_kcmil"),),
        free_text=frozenset({"commonly_replaces"}), size_field="aluminum_size_kcmil",
    ),
    "ACSR_TW.pdf": Table("ACSR/TW", {"codeword": "(?i)(.+)/TW", "size": _SIZE, "type_no": r"\d+"}, tuple(
        Region(page, 215, bottom, 20, _tw_area("Alum."),
               ((45, 135), (135, 166), (166, 198), (198, 238), (238, 275), (340, 404)),
               _TW_SECTION, "ACSR/TW:{size}:{name}:type-{type_no}", anchor="codeword")
        for page, bottom in ((2, 528.9), (3, 523.1))
    ), free_text=frozenset({"steel_wire"})),
    "ACSS TW.pdf": Table("ACSS/TW", {"codeword": "(?i)(.+)/ACSS/TW", "size": _SIZE, "type_no": r"\d+"}, (
        Region(2, 190, 560.0, 23, _tw_area("Aluminum"),
               ((40, 127), (127, 160), (160, 181), (181, 212), (212, 245), (294, 338)),
               _TW_SECTION, "ACSS/TW:{size}:{name}:type-{type_no}", anchor="codeword"),
        Region(3, 190, 452.8, 16, _tw_area("Aluminum"),
               ((40, 134), (134, 168), (168, 188), (188, 219), (219, 252), (298, 340)),
               _TW_SECTION, "ACSS/TW:{size}:{name}:type-{type_no}", anchor="codeword"),
    ), free_text=frozenset({"steel_wire"})),
    "ACSS Hs285.pdf": Table("ACSS/TW", {"codeword": "(?i)(.+)/ACSS/TW", "size": _SIZE, "type_no": r"\d+"}, (
        Region(3, 145, 679.5, 38, _HS285_AREA,
               (47, 102, 136, 165, 197, 235, 266, 291, 327, 360, 393, 425, 457, 489, 521, 553),
               "Area Equal to ACSS", _HS285_KEY.replace("{prefix}", "area-equal"), anchor="codeword"),
        Region(4, 140, 680.8, 38, _HS285_ELECTRICAL, _HS285_ELECTRICAL_X, "Area Equal to ACSS",
               _HS285_KEY.replace("{prefix}", "area-equal") + ":electrical"),
        Region(5, 140, 671.5, 34, _HS285_DIAMETER,
               (44, 99, 126, 143, 171, 197, 226, 257, 282, 303, 336, 367, 399, 434, 469, 500, 528, 556),
               "Diameters Equal to ACSR", _HS285_KEY.replace("{prefix}", "diameter-equal") + ":geometry",
               unnamed_first_row=True),
        Region(6, 140, 671.5, 34, _HS285_ELECTRICAL, _HS285_ELECTRICAL_X, "Diameters Equal to ACSR",
               _HS285_KEY.replace("{prefix}", "diameter-equal") + ":electrical", unnamed_first_row=True),
    ), free_text=frozenset({"steel_wire", "acsr_stranding"})),
}


def _bins(x: tuple) -> tuple[tuple[float, float], ...]:
    if isinstance(x[0], tuple):
        return x
    edges = [(a + b) / 2 for a, b in pairwise(x)]
    return tuple(zip([-math.inf, *edges], [*edges, math.inf]))


def _column(bins: tuple[tuple[float, float], ...], x: float) -> int | None:
    return next((index for index, (left, right) in enumerate(bins) if left <= x < right), None)


def _region_cells(page: pymupdf.Page, region: Region, pattern: str) -> list[dict[str, SourceCell]]:
    words = page.get_text("words")
    bins = _bins(region.x)
    anchor = [field for field, _, _ in region.fields].index(region.anchor)
    starts = [word[1] for word in words if region.top <= word[1] < region.bottom
              and _column(bins, word[0]) == anchor and re.fullmatch(pattern, word[4])]
    if len(starts) != region.rows:
        raise ValueError(f"page {region.page}: expected {region.rows} rows, found {len(starts)}")
    rows = []
    for top, bottom in zip(starts, [start - 2 for start in starts[1:]] + [region.bottom]):
        columns: list[list[str]] = [[] for _ in bins]
        for word in words:
            column = _column(bins, word[0])
            if top - 2 <= word[1] < bottom and column is not None:
                columns[column].append(word[4])
        rows.append({field: SourceCell(header, " ".join(text) or None, unit)
                     for (field, header, unit), text in zip(region.fields, columns, strict=True)})
    return rows


def extract(path: str | Path) -> list[SourceRow]:
    """Stage every table row of one pinned PDF, chosen by file name."""
    source = Path(path)
    table = TABLES[source.name]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    staged: list[SourceRow] = []
    with pymupdf.open(source) as document:
        for region in table.regions:
            pattern = table.patterns[region.anchor]
            for index, cells in enumerate(_region_cells(document[region.page - 1], region, pattern)):
                raw = {field: cell.raw for field, cell in cells.items()}
                unnamed = region.unnamed_first_row and index == 0 and raw["codeword"] is None
                for field, field_pattern in table.patterns.items():
                    if not (unnamed and field == "codeword") and not re.fullmatch(field_pattern, raw[field] or ""):
                        raise ValueError(f"{source.name} page {region.page}: invalid {field} {raw[field]!r}")
                for field in raw.keys() - table.patterns.keys() - table.free_text:
                    parse_numeric_cell(raw[field])
                codeword = None if unnamed else re.fullmatch(table.patterns["codeword"], raw["codeword"]).group(1)
                size = raw[table.size_field]
                size = size if "/" in size else format(Decimal(size).normalize(), "f")
                name = codeword.casefold() if codeword else "unnamed"
                key = region.key.format_map(raw | {"size": size, "name": name, "slug": name.replace(" ", "-"),
                                                   "variant": region.variant})
                staged.append(SourceRow(source_file=source, source_sha256=digest, page=region.page,
                                        section=region.section, table=table.name, row_key=key,
                                        codeword=codeword, size=size, cells=cells, variant=region.variant))
    if len({row.row_key for row in staged}) != len(staged):
        raise ValueError(f"{source.name}: duplicate row keys")
    return staged
