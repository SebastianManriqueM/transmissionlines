"""Check ACCC variant identities before catalog publication."""

from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from transmissionlines.catalog.accc_pdf import extract_accc
from transmissionlines.catalog.accc_variants import stage_accc_variants


PDF = Path(__file__).resolve().parents[2] / "data/raw/conductors/ACCC_electrical_data_ctc.pdf"


def test_accc_variant_ids_and_strengths_are_source_backed() -> None:
    rows = extract_accc(PDF)
    records = stage_accc_variants(rows)

    assert len(records) == 48
    assert Counter(record.variant for record in records) == {"standard": 28, "uls": 20}
    assert len({record.record_id for record in records}) == len(records)
    assert {record.record_id for record in records} == {
        record.record_id for record in stage_accc_variants(reversed(rows))
    }
    oceanside = next(record for record in records if record.codeword == "OCEANSIDE")
    assert oceanside.record_id == "ACCC:383.2:oceanside:standard"
    assert oceanside.rated_strength_lb == Decimal("16000")
    assert oceanside.source.row_key == "ACCC:383.2:oceanside"
    assert all(record.variant == "standard" for record in records if record.codeword == "OCEANSIDE")

    irving = {record.variant: record for record in records if record.codeword == "IRVING"}
    assert set(irving) == {"standard", "uls"}
    assert irving["standard"].rated_strength_lb == Decimal("33200")
    assert irving["uls"].record_id == "ACCC:609.5:irving:uls"
    assert irving["uls"].rated_strength_lb == Decimal("39000")
    assert irving["uls"].rated_strength_cell.raw == "39.0"
    assert irving["uls"].rated_strength_cell.unit == "klbf"
    assert irving["uls"].source is irving["standard"].source
    assert irving["uls"].weight_total_lb_kft is None
    assert irving["standard"].weight_total_lb_kft == Decimal("648.3")


def test_accc_missing_standard_strength_is_rejected() -> None:
    oceanside = extract_accc(PDF)[0]
    cells = dict(oceanside.cells)
    cells["strength_standard_klbf"] = replace(cells["strength_standard_klbf"], raw=None)

    with pytest.raises(ValueError, match="missing ACCC standard strength"):
        stage_accc_variants([replace(oceanside, cells=cells)])


def test_accc_duplicate_variant_ids_are_rejected() -> None:
    oceanside = extract_accc(PDF)[0]

    with pytest.raises(ValueError, match="duplicate ACCC variant ID"):
        stage_accc_variants([oceanside, oceanside])


def test_accc_empty_source_does_not_generate_variants() -> None:
    assert stage_accc_variants([]) == []