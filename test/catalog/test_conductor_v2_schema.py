"""Check v2 conductor contracts without changing the v1 catalog."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from transmissionlines.catalog.schemas import (
    ConductorRecord, ConductorV2Record, ConductorFieldProvenance, TABLE_MODELS,
)


def test_v2_conductor_fields_do_not_change_v1_schema() -> None:
    assert TABLE_MODELS["conductors"] is ConductorRecord
    with pytest.raises(ValidationError):
        ConductorRecord.model_validate({
            "record_id": "ACSS:266.8:partridge:standard", "source_id": "pdf",
            "family": "ACSS", "codeword": "Partridge", "variant": "standard",
        })

    record = ConductorV2Record.model_validate({
        "record_id": "ACSS:266.8:partridge:standard", "source_id": "pdf",
        "family": "ACSS", "codeword": "Partridge", "variant": "standard",
        "weight_lb_kft": Decimal("548"), "rated_strength_lb": Decimal("8880"),
        "aluminum_area_in2": Decimal("0.244"), "core_area_in2": Decimal("0.017"),
        "total_area_in2": Decimal("0.261"),
        "ac_resistance_temperature_c": 75, "ampacity_temperature_c": 75,
    })
    assert record.total_area_in2 == Decimal("0.261")
    assert record.variant == "standard"
    assert record.model_dump(mode="json")["total_area_in2"] == "0.261"


def test_v2_requires_variant_but_preserves_unknown_measurements() -> None:
    with pytest.raises(ValidationError):
        ConductorV2Record.model_validate({
            "record_id": "ACCC:irving:standard", "source_id": "pdf",
            "family": "ACCC", "codeword": "IRVING",
        })

    record = ConductorV2Record(
        record_id="ACCC:irving:uls", source_id="pdf", family="ACCC",
        codeword="IRVING", variant="uls",
    )
    assert record.core_area_in2 is None
    assert record.stranding is None
    assert record.ac_resistance_temperature_c is None


def test_field_provenance_preserves_source_and_derivation_inputs() -> None:
    provenance = ConductorFieldProvenance(
        record_id="ACSR:2156:bluebird:standard:84/19", field="total_area_in2",
        method="cross_pdf", source_id="ACSS/TW", row_key="ACSS/TW:2156:bluebird:type-8",
        source_sha256="a" * 64, page=3, source_field="total_area_in2",
        source_header="Total Area (in2)", raw_value="1.8309", unit="in2",
        input_fields=("total_area_in2",),
    )
    assert provenance.model_validate_json(provenance.model_dump_json()) == provenance
    assert provenance.raw_value == "1.8309"

    with pytest.raises(ValidationError):
        ConductorFieldProvenance.model_validate({
            **provenance.model_dump(), "method": "guessed",
        })