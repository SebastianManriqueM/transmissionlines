"""Check the conductor record shared by both catalog versions."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from transmissionlines.catalog.schemas import ConductorFieldProvenance, ConductorRecord


def test_conductor_record_keeps_pdf_measurements_as_decimals() -> None:
    record = ConductorRecord.model_validate({
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


def test_v1_columns_map_to_temperature_named_fields() -> None:
    record = ConductorRecord.model_validate({
        "record_id": "ACSR:Cardinal:954:1", "source_id": "Cardinal", "family": "ACSR",
        "codeword": "Cardinal", "dc_resistance_ohm_kft": 0.0179, "ac_resistance_ohm_kft": 0.0222,
        "ac_resistance_25_ohm_kft": 0.0184, "ac_resistance_50_ohm_kft": None,
        "ac_resistance_75_ohm_kft": 0.0222, "ampacity_a": 990.0,
    })
    assert record.variant is None
    assert record.dc_resistance_20c_ohm_kft == Decimal("0.0179")
    assert record.ac_resistance_25c_ohm_kft == Decimal("0.0184")
    assert record.ac_resistance_50c_ohm_kft is None
    assert record.ac_resistance_75c_ohm_kft == Decimal("0.0222")
    assert record.ampacity_a == 990.0 and record.ampacity_75c_a is None


def test_absent_measurements_stay_absent() -> None:
    record = ConductorRecord(
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