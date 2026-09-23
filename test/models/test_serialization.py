"""Test quantity, value-model, component-graph, and system serialization."""

import json
import math

import pytest
from pydantic import ValidationError

from transmissionlines import (
    BundleSpacing,
    ComplexMatrix,
    LineAssetComponent,
    LineDataModel,
    TowerCoordinate,
    TransmissionLineSystem,
)


class _LineGeometry(LineDataModel):
    """Represent a minimal nested value model for serialization coverage."""

    coordinate: TowerCoordinate
    bundle_spacing: BundleSpacing


class _SerializationLine(LineAssetComponent):
    """Represent a minimal named component for serialization coverage."""

    geometry: _LineGeometry


def test_quantities_validate_compatible_units_and_pydantic_round_trip() -> None:
    """Accept compatible units and retain them through Pydantic JSON serialization."""
    geometry = _LineGeometry(
        coordinate=TowerCoordinate(12, "meter"),
        bundle_spacing=BundleSpacing(0.5, "foot"),
    )

    restored = _LineGeometry.model_validate_json(geometry.model_dump_json())

    assert restored.coordinate.to("foot").magnitude == pytest.approx(39.3701)
    assert restored.bundle_spacing.to("inch").magnitude == pytest.approx(6.0)


def test_quantities_reject_incompatible_units() -> None:
    """Reject dimensions that do not match the semantic quantity type."""
    with pytest.raises(ValidationError, match="Unit must be compatible"):
        _LineGeometry(
            coordinate=TowerCoordinate(1, "second"),
            bundle_spacing=BundleSpacing(1, "inch"),
        )


def test_nested_line_data_model_serializes_inside_component(tmp_path) -> None:
    """Persist nested immutable values through an infrasys component graph."""
    system = TransmissionLineSystem(name="serialization-system")
    system.add_component(
        _SerializationLine(
            name="serialization-line",
            geometry=_LineGeometry(
                coordinate=TowerCoordinate(40, "foot"),
                bundle_spacing=BundleSpacing(18, "inch"),
            ),
        )
    )
    path = tmp_path / "serialization-system.json"

    system.to_json(path)
    restored = TransmissionLineSystem.from_json(path)
    line = restored.get_component(_SerializationLine, "serialization-line")

    assert line.geometry.coordinate == TowerCoordinate(40, "foot")
    assert line.geometry.bundle_spacing == BundleSpacing(18, "inch")


def test_complex_matrix_round_trips_values_and_labels() -> None:
    """Preserve explicit real and imaginary arrays with matrix labels."""
    matrix = ComplexMatrix(
        rows=2,
        columns=2,
        unit="ohm / mile",
        row_labels=["phase-a", "phase-b"],
        column_labels=["phase-a", "phase-b"],
        real=[[1.0, 0.1], [0.1, 1.2]],
        imaginary=[[2.0, 0.2], [0.2, 2.4]],
    )

    restored = ComplexMatrix.model_validate_json(matrix.model_dump_json())

    assert restored == matrix
    assert restored.as_array().tolist() == [
        [1 + 2j, 0.1 + 0.2j],
        [0.1 + 0.2j, 1.2 + 2.4j],
    ]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_complex_matrix_rejects_non_finite_values(value: float) -> None:
    """Reject values that cannot round-trip through JSON."""
    with pytest.raises(ValidationError, match="finite"):
        ComplexMatrix(
            rows=1,
            columns=1,
            unit="ohm / mile",
            row_labels=["phase-a"],
            column_labels=["phase-a"],
            real=[[value]],
            imaginary=[[0.0]],
        )


def test_complex_matrix_normalizes_values_to_immutable_containers() -> None:
    """Preserve validated matrix shape after construction."""
    matrix = ComplexMatrix(
        rows=1,
        columns=1,
        unit="ohm / mile",
        row_labels=["phase-a"],
        column_labels=["phase-a"],
        real=[[1.0]],
        imaginary=[[0.0]],
    )

    assert matrix.row_labels == ("phase-a",)
    assert matrix.real == ((1.0,),)
    with pytest.raises(AttributeError):
        matrix.real[0].append(2.0)


def test_system_json_round_trips_minimal_component_graph(tmp_path) -> None:
    """Restore a deterministically named component graph from JSON."""
    system = TransmissionLineSystem(name="minimal-graph")
    system.add_component(
        _SerializationLine(
            name="minimal-line",
            geometry=_LineGeometry(
                coordinate=TowerCoordinate(1, "foot"),
                bundle_spacing=BundleSpacing(1, "inch"),
            ),
        )
    )
    path = tmp_path / "minimal-graph.json"

    system.to_json(path)
    restored = TransmissionLineSystem.from_json(path)

    assert restored.name == "minimal-graph"
    assert (
        restored.get_component(_SerializationLine, "minimal-line").name
        == "minimal-line"
    )


def test_system_writes_schema_version_and_rejects_unsupported_versions(
    tmp_path,
) -> None:
    """Write project metadata and reject serialized data from unknown schemas."""
    system = TransmissionLineSystem(name="versioned-system")
    path = tmp_path / "versioned-system.json"

    system.to_json(path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["transmissionlines_schema_version"] == "0.1"
    payload["transmissionlines_schema_version"] = "999.0"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Unsupported transmissionlines schema version",
    ):
        TransmissionLineSystem.from_json(path)