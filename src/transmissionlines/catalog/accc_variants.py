"""Normalize ACCC source strengths into distinct, unpublished variants."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Literal

from transmissionlines.catalog.accc_pdf import ACCCSourceRow
from transmissionlines.catalog.acsr_pdf import SourceCell


@dataclass(frozen=True, kw_only=True)
class ACCCVariant:
    """Retain one standard or ULS strength choice with its printed source row."""

    record_id: str
    family: Literal["ACCC"]
    codeword: str
    size_kcmil: Decimal
    variant: Literal["standard", "uls"]
    rated_strength_lb: Decimal
    rated_strength_cell: SourceCell
    weight_total_lb_kft: Decimal | None
    source: ACCCSourceRow


def stage_accc_variants(rows: Iterable[ACCCSourceRow]) -> list[ACCCVariant]:
    """Stage ACCC strength variants using the shared row's total weight.

    Parameters
    ----------
    rows : Iterable[ACCCSourceRow]
        ACCC PDF rows with separately printed standard and ULS strengths.

    Returns
    -------
    list[ACCCVariant]
        One standard variant per source row and a ULS variant only when its
        rated strength is numeric. ULS reuses the printed row weight as an
        approximation, not a separately published ULS measurement.

    Raises
    ------
    ValueError
        If standard strength is absent or deterministic IDs collide.
    """
    staged: list[ACCCVariant] = []
    identities: set[str] = set()
    for row in rows:
        standard_strength = row.numeric("strength_standard_klbf")
        if standard_strength is None:
            raise ValueError(f"missing ACCC standard strength: {row.row_key}")
        for variant, strength in (("standard", standard_strength), ("uls", row.numeric("strength_uls_klbf"))):
            if strength is None:
                continue
            record_id = f"{row.row_key}:{variant}"
            if record_id in identities:
                raise ValueError(f"duplicate ACCC variant ID: {record_id}")
            identities.add(record_id)
            strength_field = "strength_standard_klbf" if variant == "standard" else "strength_uls_klbf"
            staged.append(ACCCVariant(
                record_id=record_id, family="ACCC", codeword=row.codeword,
                size_kcmil=Decimal(row.size), variant=variant,
                rated_strength_lb=strength * 1000,
                rated_strength_cell=row.cells[strength_field],
                weight_total_lb_kft=row.numeric("weight_total_lb_kft"),
                source=row,
            ))
    return staged