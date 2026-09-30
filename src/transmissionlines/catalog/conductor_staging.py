"""Normalize PDF source rows into unpublished conductor candidates."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from transmissionlines.catalog.aac_pdf import AACSourceRow
from transmissionlines.catalog.accc_pdf import ACCCSourceRow
from transmissionlines.catalog.accc_variants import stage_accc_variants
from transmissionlines.catalog.acsr_aw_pdf import ACSRAWSourceRow
from transmissionlines.catalog.acsr_pdf import ACSRSourceRow, SourceCell
from transmissionlines.catalog.acss_hs285_tw_pdf import HS285TWSourceRow
from transmissionlines.catalog.acss_pdf import ACSSSourceRow


SourceRow = ACSRSourceRow | ACSRAWSourceRow | ACSSSourceRow | AACSourceRow | ACCCSourceRow | HS285TWSourceRow


@dataclass(frozen=True, kw_only=True)
class ConductorCandidate:
    """Retain a stable strength identity and its original PDF cells."""

    record_id: str
    family: str
    codeword: str | None
    size: str
    variant: str
    rated_strength_lb: Decimal
    strength_cell: SourceCell
    weight_total_lb_kft: Decimal | None
    weight_cell: SourceCell
    weight_basis: str
    source: SourceRow


@dataclass(frozen=True, kw_only=True)
class StagingIssue:
    """Identify an unresolved source cell or candidate without inventing a value."""

    row_key: str
    reason: str
    field: str


@dataclass(frozen=True, kw_only=True)
class StagingResult:
    """Group unpublished conductor candidates and their audit issues."""

    candidates: list[ConductorCandidate]
    issues: list[StagingIssue]


def stage_acss(rows: Iterable[ACSSSourceRow]) -> list[ConductorCandidate]:
    """Stage one ACSS candidate for each printed strength grade.

    Parameters
    ----------
    rows : Iterable[ACSSSourceRow]
        Round-wire source rows from the ACSS PDF.

    Returns
    -------
    list[ConductorCandidate]
        Source-backed candidates with stable grade-specific identities.

    Raises
    ------
    ValueError
        If a deterministic candidate identity repeats.
    """
    candidates: list[ConductorCandidate] = []
    identities: set[str] = set()
    for row in rows:
        for variant in ("standard", "high", "hs285"):
            field = f"strength_{variant}_lb"
            strength = row.numeric(field)
            if strength is None:
                continue
            record_id = f"{row.row_key}:{variant}"
            if record_id in identities:
                raise ValueError(f"duplicate conductor ID: {record_id}")
            identities.add(record_id)
            candidates.append(ConductorCandidate(
                record_id=record_id, family="ACSS", codeword=row.codeword,
                size=row.size, variant=variant, rated_strength_lb=strength,
                strength_cell=row.cells[field], weight_total_lb_kft=row.numeric("weight_total_lb_kft"),
                weight_cell=row.cells["weight_total_lb_kft"], weight_basis="published", source=row,
            ))
    return candidates


def stage_sources(
    *,
    acsr: Iterable[ACSRSourceRow] = (),
    acsr_aw: Iterable[ACSRAWSourceRow] = (),
    acss: Iterable[ACSSSourceRow] = (),
    aac: Iterable[AACSourceRow] = (),
    accc: Iterable[ACCCSourceRow] = (),
    hs285_tw: Iterable[HS285TWSourceRow] = (),
) -> StagingResult:
    """Stage strength-backed PDF candidates without writing catalog files.

    Parameters
    ----------
    acsr, acsr_aw, acss, aac, accc, hs285_tw : Iterable[SourceRow]
        Previously extracted source rows, separated by manufacturer layout.

    Returns
    -------
    StagingResult
        Candidates and a row-keyed audit of absent strength cells.

    Raises
    ------
    ValueError
        If deterministic IDs collide or an ACCC standard strength is missing.
    """
    candidates: list[ConductorCandidate] = []
    issues: list[StagingIssue] = []
    identities: set[str] = set()

    def add(row: SourceRow, *, family: str, variant: str, field: str) -> None:
        strength = row.numeric(field)
        if strength is None:
            issues.append(StagingIssue(row_key=row.row_key, reason="missing_strength", field=field))
            return
        record_id = row.row_key if family in {"ACSR", "ACSR/AW"} else f"{row.row_key}:{variant}"
        if record_id in identities:
            raise ValueError(f"duplicate conductor ID: {record_id}")
        identities.add(record_id)
        candidates.append(ConductorCandidate(
            record_id=record_id, family=family, codeword=row.codeword,
            size=row.size, variant=variant, rated_strength_lb=strength,
            strength_cell=row.cells[field], weight_total_lb_kft=row.numeric("weight_total_lb_kft"),
            weight_cell=row.cells["weight_total_lb_kft"], weight_basis="published", source=row,
        ))

    for row in acsr:
        add(row, family="ACSR", variant=row.variant, field="rated_strength_lb")
    for row in acsr_aw:
        add(row, family="ACSR/AW", variant=row.variant, field="rated_strength_lb")
    for row in acss:
        for variant in ("standard", "high", "hs285"):
            add(row, family="ACSS", variant=variant, field=f"strength_{variant}_lb")
    for row in aac:
        add(row, family="AAC", variant="standard", field="rated_strength_lb")
    for row in accc:
        for staged in stage_accc_variants([row]):
            if staged.record_id in identities:
                raise ValueError(f"duplicate conductor ID: {staged.record_id}")
            identities.add(staged.record_id)
            candidates.append(ConductorCandidate(
                record_id=staged.record_id, family="ACCC", codeword=row.codeword,
                size=row.size, variant=staged.variant, rated_strength_lb=staged.rated_strength_lb,
                strength_cell=staged.rated_strength_cell, weight_total_lb_kft=staged.weight_total_lb_kft,
                weight_cell=row.cells["weight_total_lb_kft"],
                weight_basis="shared_approximation" if staged.variant == "uls" else "published",
                source=row,
            ))
        if row.numeric("strength_uls_klbf") is None:
            issues.append(StagingIssue(row_key=row.row_key, reason="missing_strength", field="strength_uls_klbf"))
    for row in hs285_tw:
        if "strength_standard_lb" not in row.cells:
            continue
        for variant in ("standard", "high", "hs285"):
            add(row, family="ACSS/TW", variant=variant, field=f"strength_{variant}_lb")
    return StagingResult(candidates=candidates, issues=issues)