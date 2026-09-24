import pytest

from transmissionlines.models.electrical import MatrixResult
from transmissionlines.system import upgrade_transmissionlines_system_data


def test_legacy_matrix_payloads_are_migrated_to_typed_results() -> None:
    data = {
        "data_format_version": "2.0.0",
        "transmissionlines_schema_version": "2.0.0",
        "electrical_parameters": {
            "status": "complete",
            "labels": ["A"],
            "matrices": {"Z_kron": [[{"real": 1.0, "imag": 2.0}]]},
        },
    }
    upgrade_transmissionlines_system_data(data, from_version="2.0.0", to_version="3.0.0")
    migrated = data["electrical_parameters"]["matrices"]["Z_kron"]
    assert migrated["name"] == "Z_kron"
    assert migrated["real"] == [[1.0]]
    assert migrated["imaginary"] == [[2.0]]
    assert data["electrical_parameters"]["status"] == "incomplete"


def test_matrix_result_has_explicit_json_safe_metadata() -> None:
    result = MatrixResult(
        name="Z",
        row_count=1,
        column_count=1,
        row_labels=["A"],
        column_labels=["A"],
        unit="ohm/mile",
        real=[[1.0]],
        imaginary=[[2.0]],
    )
    restored = MatrixResult.model_validate_json(result.model_dump_json())
    assert restored.name == "Z"
    assert restored.cells == [[{"real": 1.0, "imag": 2.0}]]
    assert list(restored) == restored.cells
    assert restored[0] == restored.cells[0]
    with pytest.raises(ValueError, match="row counts"):
        MatrixResult(name="bad", row_count=2, column_count=1, unit="ohm/mile", real=[[1.0]], imaginary=[[0.0]])
