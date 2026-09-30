"""Resolve unpublished material areas with source-cell provenance and audit issues."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Literal

from transmissionlines.catalog.acsr_pdf import SourceCell
from transmissionlines.catalog.acsr_tw_pdf import TWAreaSourceRow
from transmissionlines.catalog.acss_tw_pdf import ACSSTWAreaSourceRow
from transmissionlines.catalog.conductor_staging import (
    ConductorCandidate, SourceRow, StagingIssue, StagingResult,
)


PI_OVER_FOUR = Decimal("0.7853981633974483096156608458")
GEOMETRY_TOLERANCE = Decimal("0.02")
ENVELOPE_TOLERANCE = Decimal("0.01")
PRINTED_AREA_TOLERANCE = Decimal("0.0002")
TW_TOTAL_COMPARISON_TOLERANCE = Decimal("0.0006")
TWRow = TWAreaSourceRow | ACSSTWAreaSourceRow


@dataclass(frozen=True, kw_only=True)
class AreaInput:
    """Link a calculation to a printed field and original cell."""

    field: str
    cell: SourceCell


@dataclass(frozen=True, kw_only=True)
class AreaValue:
    """Retain square-inch material area and its provenance or assumption."""

    value: Decimal
    method: Literal["published", "cross_pdf", "derived", "assumed"]
    source_rows: tuple[SourceRow | TWRow, ...]
    input_cells: tuple[AreaInput, ...]
    note: str = ""


@dataclass(frozen=True, kw_only=True)
class MechanicalArea:
    """Keep aluminum, core, and total material area separate."""

    aluminum: AreaValue
    core: AreaValue | None
    total: AreaValue


@dataclass(frozen=True, kw_only=True)
class AreaCandidate:
    """Pair a strength candidate with its resolved or missing area."""

    candidate: ConductorCandidate
    area: MechanicalArea | None


@dataclass(frozen=True, kw_only=True)
class AreaStageResult:
    """Return candidates and row-keyed, field-specific audit findings."""

    records: list[AreaCandidate]
    issues: list[StagingIssue]


def _inputs(row: SourceRow | TWRow, *fields: str) -> tuple[AreaInput, ...]:
    return tuple(AreaInput(field=field, cell=row.cells[field]) for field in fields)


def _round_geometry(row: SourceRow) -> MechanicalArea | None:
    if row.table not in {"ACSR", "ACSR/AW", "ACSS"}:
        return None
    core_field = {"ACSR": "strand_diameter_stl_in", "ACSR/AW": "strand_diameter_aw_in",
                  "ACSS": "strand_diameter_steel_in"}[row.table]
    raw = row.cells["stranding"].raw
    aluminum_diameter = row.numeric("strand_diameter_al_in")
    core_diameter = row.numeric(core_field)
    if not raw or aluminum_diameter is None or core_diameter is None:
        return None
    try:
        aluminum_count, core_count = (int(part) for part in raw.split("/"))
    except ValueError:
        return None
    if aluminum_count <= 0 or core_count <= 0 or aluminum_diameter <= 0 or core_diameter <= 0:
        return None
    aluminum = PI_OVER_FOUR * aluminum_count * aluminum_diameter ** 2
    core = PI_OVER_FOUR * core_count * core_diameter ** 2
    common = _inputs(row, "stranding", "strand_diameter_al_in", core_field)
    return MechanicalArea(
        aluminum=AreaValue(value=aluminum, method="derived", source_rows=(row,), input_cells=common),
        core=AreaValue(value=core, method="derived", source_rows=(row,), input_cells=common),
        total=AreaValue(value=aluminum + core, method="derived", source_rows=(row,), input_cells=common),
    )


def _from_tw(row: TWRow) -> MechanicalArea | None:
    aluminum = row.numeric("aluminum_area_in2")
    total = row.numeric("total_area_in2")
    if aluminum is None or total is None or not 0 < aluminum <= total:
        return None
    aluminum_input = _inputs(row, "aluminum_area_in2")
    total_input = _inputs(row, "total_area_in2")
    return MechanicalArea(
        aluminum=AreaValue(value=aluminum, method="cross_pdf", source_rows=(row,), input_cells=aluminum_input),
        core=AreaValue(value=total - aluminum, method="cross_pdf", source_rows=(row,),
                       input_cells=aluminum_input + total_input),
        total=AreaValue(value=total, method="cross_pdf", source_rows=(row,), input_cells=total_input),
    )


def _area_mismatch(transfer: MechanicalArea, derived: MechanicalArea) -> tuple[str, Decimal, Decimal] | None:
    for field in ("aluminum", "core", "total"):
        transfer_value = getattr(transfer, field)
        derived_value = getattr(derived, field)
        if transfer_value is not None and derived_value is not None and abs(transfer_value.value - derived_value.value) > (
            derived_value.value * GEOMETRY_TOLERANCE + PRINTED_AREA_TOLERANCE
        ):
            return field, derived_value.value, transfer_value.value
    return None


def _index(rows: Iterable[TWRow]) -> dict[tuple[str, str], list[TWRow]]:
    index: dict[tuple[str, str], list[TWRow]] = defaultdict(list)
    for row in rows:
        index[(row.codeword.casefold().strip(), row.size)].append(row)
    return index


def _accc_area(candidate: ConductorCandidate) -> MechanicalArea | None:
    row = candidate.source
    aluminum_size = row.numeric("aluminum_size_kcmil")
    core_diameter = row.numeric("core_diameter_in")
    if aluminum_size is None or core_diameter is None or aluminum_size <= 0 or core_diameter <= 0:
        return None
    aluminum = aluminum_size * PI_OVER_FOUR / 1000
    core = PI_OVER_FOUR * core_diameter ** 2
    assumed = candidate.variant == "uls"
    note = "Assume the standard row's core diameter applies to ULS" if assumed else ""
    aluminum_input = _inputs(row, "aluminum_size_kcmil")
    core_input = _inputs(row, "core_diameter_in")
    return MechanicalArea(
        aluminum=AreaValue(value=aluminum, method="derived", source_rows=(row,), input_cells=aluminum_input),
        core=AreaValue(value=core, method="assumed" if assumed else "derived", source_rows=(row,),
                       input_cells=core_input, note=note),
        total=AreaValue(value=aluminum + core, method="assumed" if assumed else "derived",
                        source_rows=(row,), input_cells=aluminum_input + core_input, note=note),
    )


def _own_area(candidate: ConductorCandidate) -> MechanicalArea | None:
    row = candidate.source
    if candidate.family == "ACCC":
        return _accc_area(candidate)
    if candidate.family == "AAC":
        published = row.numeric("aluminum_area_in2")
        if published is None or published <= 0:
            return None
        value = AreaValue(value=published, method="published", source_rows=(row,),
                          input_cells=_inputs(row, "aluminum_area_in2"))
        return MechanicalArea(aluminum=value, core=None, total=value)
    if candidate.family == "ACSS/TW":
        aluminum = row.numeric("aluminum_area_in2")
        total = row.numeric("total_area_in2")
        if aluminum is None or total is None or not 0 < aluminum <= total:
            return None
        al_input = _inputs(row, "aluminum_area_in2")
        total_input = _inputs(row, "total_area_in2")
        return MechanicalArea(
            aluminum=AreaValue(value=aluminum, method="published", source_rows=(row,), input_cells=al_input),
            core=AreaValue(value=total - aluminum, method="published", source_rows=(row,),
                           input_cells=al_input + total_input),
            total=AreaValue(value=total, method="published", source_rows=(row,), input_cells=total_input),
        )
    return _round_geometry(row)


def resolve_areas(
    staged: StagingResult, *,
    acsr_tw: Iterable[TWAreaSourceRow] = (),
    acss_tw: Iterable[ACSSTWAreaSourceRow] = (),
) -> AreaStageResult:
    """Resolve candidate material areas, quarantining incompatible transfers.

    Parameters
    ----------
    staged : StagingResult
        Strength-backed unpublished candidates and existing audit issues.
    acsr_tw, acss_tw : Iterable
        Published equal-area reference rows, kept separate by family.

    Returns
    -------
    AreaStageResult
        Areas with field-level provenance and all unresolved conditions.

    Notes
    -----
    Compare TW aluminum, core, and total areas with strand-derived areas within
    2 percent, allowing printed precision; compare overlapping TW values
    within 0.0006 square inches. Reject areas exceeding the outside-diameter
    envelope by more than 1 percent for printed dimension precision.
    """
    acsr_index = _index(acsr_tw)
    acss_index = _index(acss_tw)
    issues = list(staged.issues)
    records: list[AreaCandidate] = []
    for candidate in staged.candidates:
        row = candidate.source
        area = _own_area(candidate)
        if candidate.family in {"ACSR", "ACSR/AW", "ACSS"}:
            key = (candidate.codeword.casefold().strip(), candidate.size)
            preferred, alternate = ((acss_index, acsr_index) if candidate.family == "ACSS"
                                    else (acsr_index, acss_index))
            for matches in (preferred.get(key, []), alternate.get(key, [])):
                if len(matches) > 1:
                    issues.append(StagingIssue(row_key=row.row_key, reason="ambiguous_tw_area", field="total_area_in2"))
            first = preferred.get(key, [])
            second = alternate.get(key, [])
            if len(first) == len(second) == 1:
                a, b = first[0].numeric("total_area_in2"), second[0].numeric("total_area_in2")
                if a is not None and b is not None and a != b:
                    reason = "tw_area_disagreement" if abs(a - b) > TW_TOTAL_COMPARISON_TOLERANCE else "tw_area_rounding_difference"
                    issues.append(StagingIssue(row_key=row.row_key, reason=reason, field="total_area_in2",
                                               source_values=((first[0], a), (second[0], b))))
            geometry = area
            for matches in (first, second):
                if len(matches) != 1:
                    continue
                transfer = _from_tw(matches[0])
                mismatch = _area_mismatch(transfer, geometry) if transfer is not None and geometry is not None else None
                if transfer is None or geometry is None or mismatch is not None:
                    field = f"{mismatch[0]}_area_in2" if mismatch is not None else "total_area_in2"
                    values = ((row, mismatch[1]), (matches[0], mismatch[2])) if mismatch is not None else ()
                    issues.append(StagingIssue(row_key=row.row_key, reason="incompatible_tw_area",
                                               field=field, source_values=values))
                    continue
                area = transfer
                break
        if area is None:
            issues.append(StagingIssue(row_key=row.row_key, reason="missing_geometry", field="total_area_in2"))
        else:
            outside = row.numeric("diameter_in")
            if outside is not None and (outside <= 0 or area.total.value > PI_OVER_FOUR * outside ** 2 * (1 + ENVELOPE_TOLERANCE)):
                issues.append(StagingIssue(row_key=row.row_key, reason="area_exceeds_envelope", field="total_area_in2"))
                area = None
        records.append(AreaCandidate(candidate=candidate, area=area))
    return AreaStageResult(records=records, issues=issues)