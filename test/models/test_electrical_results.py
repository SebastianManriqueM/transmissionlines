import pytest

from transmissionlines.models.electrical import MatrixResult


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
    with pytest.raises(ValueError, match="row counts"):
        MatrixResult(name="bad", row_count=2, column_count=1, unit="ohm/mile", real=[[1.0]], imaginary=[[0.0]])
